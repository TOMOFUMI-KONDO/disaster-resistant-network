CREATE TABLE IF NOT EXISTS networks
(
    id         INT PRIMARY KEY AUTO_INCREMENT,
    name       VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_atTIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE = INNODB;

CREATE TABLE IF NOT EXISTS experiments
(
    id         INT PRIMARY KEY AUTO_INCREMENT,
    network_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (network_id) REFERENCES networks (id)
) ENGINE = INNODB;

CREATE TABLE IF NOT EXISTS backup_pairs
(
    experiment_id INT,
    name VARCHAR(255),
    data_size_gb  BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (experiment_id, name),
    FOREIGN KEY (experiment_id) REFERENCES experiments (id)
) ENGINE = INNODB;

CREATE TABLE IF NOT EXISTS benchmarks
(
    backup_pair_id        INT PRIMARY KEY,
    received_data_size_gb BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (backup_pair_id) REFERENCES backup_pairs (id)
) ENGINE = INNODB;