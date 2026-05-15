-- ============================================================
-- Scout Bot — Oracle Database schema
-- Запускать в SQL Developer Web (Oracle Cloud Console)
-- ============================================================

-- Скауты
CREATE TABLE scouts (
    user_id     NUMBER          NOT NULL,
    username    VARCHAR2(100),
    full_name   VARCHAR2(200),
    created_at  TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT  pk_scouts       PRIMARY KEY (user_id)
);

-- Отчёты о перемещении самокатов
CREATE TABLE reports (
    id          NUMBER          GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    scout_id    NUMBER          NOT NULL,
    msg_time    TIMESTAMP       NOT NULL,
    raw_text    VARCHAR2(2000),
    parking     VARCHAR2(300),
    scooter_cnt NUMBER          DEFAULT 0,
    CONSTRAINT  fk_rep_scout    FOREIGN KEY (scout_id) REFERENCES scouts (user_id)
);

-- Перерывы (обед / ужин)
CREATE TABLE breaks (
    id          NUMBER          GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    scout_id    NUMBER          NOT NULL,
    break_type  VARCHAR2(20),   -- 'lunch' | 'dinner' | 'break'
    start_time  TIMESTAMP       NOT NULL,
    end_time    TIMESTAMP,
    CONSTRAINT  fk_brk_scout    FOREIGN KEY (scout_id) REFERENCES scouts (user_id)
);

-- Простои (> IDLE_THRESHOLD_MIN, без учёта перерывов)
CREATE TABLE idle_logs (
    id          NUMBER          GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    scout_id    NUMBER          NOT NULL,
    idle_start  TIMESTAMP       NOT NULL,
    idle_end    TIMESTAMP,
    gap_minutes NUMBER,
    CONSTRAINT  fk_idle_scout   FOREIGN KEY (scout_id) REFERENCES scouts (user_id)
);

-- Индексы
CREATE INDEX idx_reports_scout_time ON reports   (scout_id, msg_time);
CREATE INDEX idx_breaks_scout_time  ON breaks    (scout_id, start_time);
CREATE INDEX idx_idle_scout_time    ON idle_logs (scout_id, idle_start);

-- Проверка
SELECT table_name FROM user_tables
WHERE table_name IN ('SCOUTS','REPORTS','BREAKS','IDLE_LOGS')
ORDER BY table_name;
