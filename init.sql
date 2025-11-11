-- Initialize database schema for Willhaben scraper

-- Create listings table
-- Using link as primary key since it's always unique
-- id can be NULL if not extracted from some listings
CREATE TABLE IF NOT EXISTS listings (
    link TEXT PRIMARY KEY,
    id VARCHAR(50),
    listing_name TEXT NOT NULL,
    price VARCHAR(50),
    address TEXT,
    apart_size VARCHAR(20),
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index on id for faster lookups (where id is not null)
CREATE INDEX IF NOT EXISTS idx_listings_id ON listings(id) WHERE id IS NOT NULL AND id != '';

-- Create index on first_seen_at for new listing detection
CREATE INDEX IF NOT EXISTS idx_listings_first_seen ON listings(first_seen_at DESC);

-- Create scraper_runs table for tracking executions
CREATE TABLE IF NOT EXISTS scraper_runs (
    id SERIAL PRIMARY KEY,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP,
    listings_found INTEGER DEFAULT 0,
    new_listings INTEGER DEFAULT 0,
    updated_listings INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'running',
    error_message TEXT
);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to auto-update updated_at
CREATE TRIGGER update_listings_updated_at BEFORE UPDATE ON listings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Comments for documentation
COMMENT ON TABLE listings IS 'Stores apartment listings from Willhaben';
COMMENT ON COLUMN listings.id IS 'Listing ID from Willhaben';
COMMENT ON COLUMN listings.first_seen_at IS 'When this listing was first scraped';
COMMENT ON COLUMN listings.last_seen_at IS 'When this listing was last seen in a scrape';
COMMENT ON TABLE scraper_runs IS 'Tracks each execution of the scraper';
