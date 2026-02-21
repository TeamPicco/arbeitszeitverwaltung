-- Inventur-Modul für Arbeitszeitverwaltung
-- Erstellt: 2026-02-21
-- Version: 3 (ohne RLS Policies wegen Typ-Konflikt)

-- Tabelle: inventur_kategorien
-- Speichert die Kategorien (z.B. Fassbiere, Fleisch, Gemüse)
CREATE TABLE IF NOT EXISTS inventur_kategorien (
    id BIGSERIAL PRIMARY KEY,
    betrieb_id BIGINT NOT NULL REFERENCES betriebe(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    beschreibung TEXT,
    sortierung INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabelle: inventur_artikel
-- Speichert die Artikel (z.B. Becks Pils 30l, Rinderfilet)
CREATE TABLE IF NOT EXISTS inventur_artikel (
    id BIGSERIAL PRIMARY KEY,
    betrieb_id BIGINT NOT NULL REFERENCES betriebe(id) ON DELETE CASCADE,
    kategorie_id BIGINT NOT NULL REFERENCES inventur_kategorien(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    einheit VARCHAR(50) NOT NULL, -- z.B. "30L-Fass", "kg", "Fl", "st"
    beschreibung TEXT,
    sortierung INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabelle: inventuren
-- Speichert die Inventuren (einmal pro Jahr)
CREATE TABLE IF NOT EXISTS inventuren (
    id BIGSERIAL PRIMARY KEY,
    betrieb_id BIGINT NOT NULL REFERENCES betriebe(id) ON DELETE CASCADE,
    jahr INTEGER NOT NULL,
    datum DATE NOT NULL,
    erstellt_von BIGINT REFERENCES users(id),
    status VARCHAR(50) DEFAULT 'offen', -- offen, abgeschlossen
    notizen TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(betrieb_id, jahr)
);

-- Tabelle: inventur_positionen
-- Speichert die einzelnen Zählungen pro Inventur
CREATE TABLE IF NOT EXISTS inventur_positionen (
    id BIGSERIAL PRIMARY KEY,
    inventur_id BIGINT NOT NULL REFERENCES inventuren(id) ON DELETE CASCADE,
    artikel_id BIGINT NOT NULL REFERENCES inventur_artikel(id) ON DELETE CASCADE,
    soll_bestand DECIMAL(10, 2) DEFAULT 0,
    ist_bestand DECIMAL(10, 2) DEFAULT 0,
    differenz DECIMAL(10, 2) GENERATED ALWAYS AS (ist_bestand - soll_bestand) STORED,
    notiz TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(inventur_id, artikel_id)
);

-- Indizes für Performance
CREATE INDEX IF NOT EXISTS idx_inventur_kategorien_betrieb ON inventur_kategorien(betrieb_id);
CREATE INDEX IF NOT EXISTS idx_inventur_artikel_betrieb ON inventur_artikel(betrieb_id);
CREATE INDEX IF NOT EXISTS idx_inventur_artikel_kategorie ON inventur_artikel(kategorie_id);
CREATE INDEX IF NOT EXISTS idx_inventuren_betrieb ON inventuren(betrieb_id);
CREATE INDEX IF NOT EXISTS idx_inventuren_jahr ON inventuren(jahr);
CREATE INDEX IF NOT EXISTS idx_inventur_positionen_inventur ON inventur_positionen(inventur_id);
CREATE INDEX IF NOT EXISTS idx_inventur_positionen_artikel ON inventur_positionen(artikel_id);

-- Trigger für updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_inventur_kategorien_updated_at BEFORE UPDATE ON inventur_kategorien
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_inventur_artikel_updated_at BEFORE UPDATE ON inventur_artikel
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_inventuren_updated_at BEFORE UPDATE ON inventuren
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_inventur_positionen_updated_at BEFORE UPDATE ON inventur_positionen
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- HINWEIS: RLS Policies wurden entfernt wegen Typ-Konflikt (auth.uid() = uuid, user_id = bigint)
-- Zugriffskontrolle erfolgt über die App-Logik (Admin-Check)
