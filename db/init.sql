CREATE TABLE IF NOT EXISTS networks
(
    id   INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255)
) ENGINE = INNODB;

CREATE TABLE IF NOT EXISTS experiments
(
    id         INT PRIMARY KEY AUTO_INCREMENT,
    network_id INT,
    FOREIGN KEY (network_id) REFERENCES networks (id)
) ENGINE = INNODB;

CREATE TABLE IF NOT EXISTS backup_pairs
(
    id            INT PRIMARY KEY AUTO_INCREMENT,
    experiment_id INT,
    data_size_gb  BIGINT,
    FOREIGN KEY (experiment_id) REFERENCES experiments (id)
) ENGINE = INNODB;

CREATE TABLE IF NOT EXISTS benchmarks
(
    backup_pair_id        INT PRIMARY KEY,
    received_data_size_gb BIGINT,
    FOREIGN KEY (backup_pair_id) REFERENCES backup_pairs (id)
) ENGINE = INNODB;