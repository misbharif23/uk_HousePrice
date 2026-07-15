-- =====================================================================
-- UK House Price Index — Normalized Schema
-- =====================================================================
-- Design note: the source CSV is "wide" — one row per region/month, with
-- ~50 numeric columns repeating the same 4 fields (Price, Index, 1m%Change,
-- 12m%Change) once per category (Detached, SemiDetached, Cash, Mortgage,
-- FTB, FOO, New, Old, ...). That's a classic repeating-group problem —
-- the same kind of thing First Normal Form exists to fix.
--
-- Instead of mirroring that wide structure, this schema normalizes it into
-- three tables: WHO (regions), WHAT KIND (categories), and the actual
-- MEASUREMENTS (price_history) — one row per region + category + month,
-- rather than one row per region + month with 50 columns.
-- =====================================================================

DROP TABLE IF EXISTS price_history;
DROP TABLE IF EXISTS regions;
DROP TABLE IF EXISTS categories;

-- ---------------------------------------------------------------------
-- regions: one row per geographic area (nation, region, or local authority)
-- ---------------------------------------------------------------------
CREATE TABLE regions (
    region_id      INT AUTO_INCREMENT PRIMARY KEY,
    region_name    VARCHAR(100) NOT NULL,
    area_code      VARCHAR(20)  NOT NULL,
    region_tier    ENUM('Nation', 'Region', 'Local Authority') NOT NULL,
    UNIQUE KEY uq_region_name (region_name),
    UNIQUE KEY uq_area_code (area_code)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- categories: the "kind" of price series (headline, property type,
-- funding method, buyer type, build status). Turns 10+ repeated column
-- groups in the CSV into 10 rows in this table instead.
-- ---------------------------------------------------------------------
CREATE TABLE categories (
    category_id    INT AUTO_INCREMENT PRIMARY KEY,
    category_name  VARCHAR(30) NOT NULL,
    category_group ENUM('Headline','PropertyType','Funding','BuyerType','BuildStatus') NOT NULL,
    UNIQUE KEY uq_category_name (category_name)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- price_history: the fact table. One row per region + category + month.
-- This is where the wide CSV actually gets "unpivoted" (melted) into.
-- ---------------------------------------------------------------------
CREATE TABLE price_history (
    history_id       BIGINT AUTO_INCREMENT PRIMARY KEY,
    region_id         INT NOT NULL,
    category_id        INT NOT NULL,
    price_date         DATE NOT NULL,
    average_price       DECIMAL(12,2),
    price_index         DECIMAL(10,4),
    change_1m_pct        DECIMAL(8,4),
    change_12m_pct        DECIMAL(8,4),
    sales_volume           INT,
    is_data_reliable         BOOLEAN NOT NULL DEFAULT TRUE,  -- from the Has*Breakdown flags built during cleaning
    FOREIGN KEY (region_id) REFERENCES regions(region_id),
    FOREIGN KEY (category_id) REFERENCES categories(category_id),
    UNIQUE KEY uq_region_category_date (region_id, category_id, price_date),
    INDEX idx_date (price_date),
    INDEX idx_region_date (region_id, price_date)
) ENGINE=InnoDB;
