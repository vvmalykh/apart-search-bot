"""Photo downloading and storage for apartment listings."""

import logging
import os
import re
import hashlib
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse

import requests
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from .config import HEADERS, REQUEST_TIMEOUT, PHOTO_CAROUSEL_DELAY
from .logger import get_logger

logger = logging.getLogger(__name__)
action_logger = get_logger()

# Photo storage settings
PHOTOS_BASE_DIR = os.getenv("PHOTOS_DIR", "photos")
PHOTO_TIMEOUT = int(os.getenv("PHOTO_TIMEOUT", "10000"))
MAX_PHOTOS_PER_LISTING = int(os.getenv("MAX_PHOTOS_PER_LISTING", "50"))


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to be filesystem-safe.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    # Remove special characters, keep alphanumeric, dash, underscore, dot
    sanitized = re.sub(r'[^\w\-.]', '_', filename)
    # Remove multiple underscores
    sanitized = re.sub(r'_+', '_', sanitized)
    # Limit length
    return sanitized[:200]


def get_listing_dir(link: str) -> Path:
    """
    Get directory path for storing listing photos.
    Creates hierarchical structure using MD5 hash of link.

    Args:
        link: Listing URL

    Returns:
        Path object for listing directory
    """
    # Create MD5 hash of link for unique directory name
    link_hash = hashlib.md5(link.encode()).hexdigest()

    # Create hierarchical structure: photos/ab/cd/abcd...
    # First 2 chars / next 2 chars / full hash
    level1 = link_hash[:2]
    level2 = link_hash[2:4]

    listing_dir = Path(PHOTOS_BASE_DIR) / level1 / level2 / link_hash
    return listing_dir


def extract_carousel_images(page) -> List[str]:
    """
    Extract full-size image URLs from carousel on the listing page.
    Uses network request interception to capture image URLs as they load.

    Args:
        page: Playwright Page object

    Returns:
        List of full-size image URLs from carousel
    """
    image_urls = []
    captured_image_urls = set()

    # Set up network request interception to capture image URLs
    def handle_request(request):
        url = request.url
        # Capture willhaben CDN image requests
        if 'cache.willhaben.at/mmo' in url and any(url.endswith(ext) for ext in ['.jpg', '.jpeg', '.png']):
            # Log all images for debugging
            logger.debug(f"Network request for image: ...{url[-80:]}")

            # Convert to LARGE version if not already
            url = url.replace('/SMALL/', '/LARGE/').replace('/MEDIUM/', '/LARGE/').replace('/XS/', '/LARGE/')
            url = url.replace('_thumb.jpg', '.jpg').replace('_thumb.png', '.png')

            # Filter out logos, icons, and hoved thumbnails from other listings
            if any(skip in url.lower() for skip in ['logo', 'icon', 'badge', 'willhaben_logo', '_hoved']):
                logger.debug(f"Filtered out unwanted image: ...{url[-60:]}")
            else:
                if url not in captured_image_urls:
                    captured_image_urls.add(url)
                    logger.info(f"Captured NEW image #{len(captured_image_urls)}: ...{url[-60:]}")

    page.on("request", handle_request)

    try:
        # Wait for page to fully load
        page.wait_for_timeout(3000)
        logger.info("Page loaded, looking for carousel images...")

        # Scroll page down to trigger lazy-loaded carousel images
        logger.info("Scrolling to trigger all lazy-loaded images...")
        for i in range(5):  # Scroll down 5 times
            page.evaluate("window.scrollBy(0, 500)")
            page.wait_for_timeout(800)

        # Scroll back to top
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(500)

        # Find all images with alt="Bild X von Y" (carousel images)
        # Look in both the main viewer and the thumbnail carousel
        carousel_images = page.locator('img[alt*="Bild"]').all()
        logger.info(f"Found {len(carousel_images)} potential carousel images")

        # Process each image and click its thumbnail to load full version
        seen_image_numbers = set()
        for idx, img in enumerate(carousel_images):
            try:
                alt = img.get_attribute('alt')

                # Only process images with "Bild X von Y" pattern (apartment photos)
                if not alt or 'von' not in alt.lower():
                    continue

                # Extract image number from "Bild 7 von 23"
                try:
                    image_num = int(alt.split()[1])
                    if image_num in seen_image_numbers:
                        continue  # Already processed this image number
                    seen_image_numbers.add(image_num)
                except:
                    pass

                # Click the thumbnail to load its full version in the main viewer
                try:
                    img.click(force=True)
                    page.wait_for_timeout(300)
                    logger.debug(f"Clicked thumbnail: {alt}")
                except:
                    pass

                # Scroll into view to ensure it's loaded
                try:
                    img.scroll_into_view_if_needed(timeout=2000)
                    page.wait_for_timeout(300)
                except:
                    pass

                # Try multiple attributes for lazy-loaded images
                src = (img.get_attribute('src') or
                      img.get_attribute('data-src') or
                      img.get_attribute('data-lazy-src'))

                # Also try srcset if no src found
                if not src:
                    srcset = img.get_attribute('srcset')
                    if srcset:
                        # Extract first URL from srcset
                        src = srcset.split(',')[0].strip().split()[0]

                if src and src.startswith('http'):
                    # Filter out logos and icons
                    if any(skip in src.lower() for skip in ['logo', 'icon', 'badge', 'willhaben_logo']):
                        logger.debug(f"Skipping logo/icon: {src[-50:]}")
                        continue

                    # Convert thumbnail URLs to full-size by removing _thumb suffix
                    src = src.replace('_thumb.jpg', '.jpg').replace('_thumb.png', '.png')

                    # Ensure we have LARGE version (if path-based sizing exists)
                    src = src.replace('/SMALL/', '/LARGE/').replace('/MEDIUM/', '/LARGE/').replace('/XS/', '/LARGE/')

                    if src not in image_urls:
                        image_urls.append(src)
                        logger.info(f"Extracted image {len(image_urls)}: ...{src[-60:]} (alt: {alt})")

            except Exception as e:
                logger.debug(f"Error processing image {idx}: {e}")
                continue

        logger.info(f"Extracted {len(image_urls)} images from carousel thumbnails")

        # Step 2: Navigate carousel to load ALL images into DOM
        # Find the total number of images from any "Bild X von Y" alt text
        total_images = None
        for img in carousel_images[:10]:  # Check first 10
            try:
                alt = img.get_attribute('alt')
                if alt and 'von' in alt.lower():
                    # Extract "23" from "Bild 1 von 23"
                    parts = alt.split('von')
                    if len(parts) == 2:
                        total_images = int(parts[1].strip().split()[0])
                        break
            except:
                continue

        if total_images and total_images > len(captured_image_urls):
            logger.info(f"Carousel has {total_images} total images, navigating to load all into network capture...")

            # Find navigation buttons or thumbnails to click through carousel
            try:
                # Try to find and click "next" button multiple times to load all images
                next_button_selectors = [
                    'button[aria-label*="nächste"]',  # Next button (German)
                    'button[aria-label*="next"]',      # Next button (English)
                    '[data-testid*="next"]',           # Next button by test ID
                    'button:has(svg)',                 # Button with arrow icon
                ]

                for attempt in range(total_images):
                    clicked = False
                    for selector in next_button_selectors:
                        try:
                            next_btn = page.locator(selector).first
                            if next_btn.is_visible(timeout=500):
                                next_btn.click(force=True, timeout=1000)
                                # Wait longer to allow image to load over network
                                page.wait_for_timeout(max(PHOTO_CAROUSEL_DELAY, 800))
                                logger.debug(f"Clicked next button (attempt {attempt + 1}), captured {len(captured_image_urls)} so far")
                                clicked = True
                                break
                        except:
                            continue

                    if not clicked:
                        logger.debug(f"No next button found on attempt {attempt + 1}, trying thumbnails")
                        # Try clicking thumbnails directly
                        thumbnails = page.locator('img[alt*="Bild"]').all()
                        if attempt < len(thumbnails):
                            try:
                                thumbnails[attempt].click(force=True, timeout=1000)
                                # Wait longer to allow image to load over network
                                page.wait_for_timeout(max(PHOTO_CAROUSEL_DELAY, 800))
                                logger.debug(f"Clicked thumbnail {attempt + 1}, captured {len(captured_image_urls)} so far")
                            except:
                                pass

                    # Stop if we've captured all expected images
                    if len(captured_image_urls) >= total_images:
                        logger.info(f"Captured all {total_images} images from network")
                        break

            except Exception as e:
                logger.debug(f"Error navigating carousel: {e}")

            logger.info(f"Finished carousel navigation, captured {len(captured_image_urls)} images from network")

        # Convert captured URLs to list
        image_urls = sorted(list(captured_image_urls))
        logger.info(f"Extracted {len(image_urls)} full-size images from carousel via network capture (expected: {total_images or 'unknown'})")

    except Exception as e:
        logger.error(f"Error extracting carousel images: {e}", exc_info=True)

    finally:
        # Remove event handler
        try:
            page.remove_listener("request", handle_request)
        except:
            pass

    return image_urls


def download_image(url: str, output_path: Path) -> bool:
    """
    Download a single image from URL.

    Args:
        url: Image URL
        output_path: Path to save image

    Returns:
        True if successful, False otherwise
    """
    try:
        response = requests.get(url, headers=HEADERS, timeout=10, stream=True)
        response.raise_for_status()

        # Write to file
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        logger.debug(f"Downloaded image: {output_path.name}")
        return True

    except Exception as e:
        logger.warning(f"Failed to download image {url}: {e}")
        return False


def extract_images_from_listing(url: str, headless: bool = True) -> List[str]:
    """
    Extract images from listing page by navigating carousel.

    Args:
        url: Listing URL
        headless: Run browser in headless mode

    Returns:
        List of image URLs
    """
    try:
        logger.info(f"Fetching listing page: {url}")

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=headless)

            context = browser.new_context(
                user_agent=HEADERS["User-Agent"],
                locale="de-DE",
                viewport={"width": 1920, "height": 1080}
            )

            page = context.new_page()
            page.goto(url, timeout=PHOTO_TIMEOUT, wait_until="networkidle")

            # Extract images from carousel
            image_urls = extract_carousel_images(page)

            context.close()
            browser.close()

            return image_urls

    except PlaywrightTimeoutError as e:
        logger.error(f"Timeout fetching listing page {url}: {e}")
        return []
    except Exception as e:
        logger.error(f"Failed to fetch listing page {url}: {e}")
        return []


def download_listing_photos(link: str, listing_name: str = "", headless: bool = True) -> int:
    """
    Download all photos for a listing from carousel.

    Args:
        link: Listing URL
        listing_name: Listing name (for logging)
        headless: Run browser in headless mode

    Returns:
        Number of photos successfully downloaded
    """
    logger.info(f"Downloading photos for listing: {listing_name or link}")
    action_logger.custom_action("PHOTO_DOWNLOAD_STARTED", f"Link: {link}")

    # Get listing directory
    listing_dir = get_listing_dir(link)

    # Check if photos already exist (check for actual image files, not just metadata.txt)
    if listing_dir.exists():
        image_files = [f for f in listing_dir.iterdir() if f.suffix.lower() in ['.jpg', '.jpeg', '.png']]
        if image_files:
            logger.info(f"Photos already exist for this listing ({len(image_files)} images), skipping download")
            return 0

    # Create directory
    listing_dir.mkdir(parents=True, exist_ok=True)

    # Save link to metadata file
    metadata_file = listing_dir / "metadata.txt"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        f.write(f"Link: {link}\n")
        f.write(f"Name: {listing_name}\n")

    # Extract image URLs from carousel
    image_urls = extract_images_from_listing(link, headless)

    if not image_urls:
        logger.warning(f"No images found in carousel")
        return 0

    # Download images
    downloaded_count = 0
    for idx, image_url in enumerate(image_urls, 1):
        # Generate filename from URL
        parsed = urlparse(image_url)
        filename = os.path.basename(parsed.path) or f"image_{idx}.jpg"
        filename = sanitize_filename(filename)

        # Add index prefix to maintain order
        filename = f"{idx:02d}_{filename}"

        output_path = listing_dir / filename

        if download_image(image_url, output_path):
            downloaded_count += 1

    logger.info(f"Downloaded {downloaded_count}/{len(image_urls)} photos for listing")
    action_logger.custom_action("PHOTO_DOWNLOAD_COMPLETED", f"Downloaded: {downloaded_count}, Link: {link}")

    return downloaded_count


def download_photos_for_listings(listings: List[dict], headless: bool = True) -> dict:
    """
    Download photos for multiple listings.

    Args:
        listings: List of listing dictionaries (must have 'link' key)
        headless: Run browser in headless mode

    Returns:
        Dictionary with stats (total_listings, photos_downloaded, errors)
    """
    stats = {
        'total_listings': len(listings),
        'photos_downloaded': 0,
        'errors': 0,
        'skipped': 0
    }

    for listing in listings:
        link = listing.get('link')
        if not link:
            logger.warning(f"Listing has no link, skipping: {listing}")
            stats['errors'] += 1
            continue

        try:
            count = download_listing_photos(
                link=link,
                listing_name=listing.get('listing_name', ''),
                headless=headless
            )

            if count == 0:
                stats['skipped'] += 1
            else:
                stats['photos_downloaded'] += count

        except Exception as e:
            logger.error(f"Error downloading photos for {link}: {e}")
            stats['errors'] += 1

    return stats
