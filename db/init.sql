CREATE TABLE IF NOT EXISTS networks
(
    id         INT PRIMARY KEY AUTO_INCREMENT,
    name       VARCHAR(255)                                                    NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP                             NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL
) ENGINE = INNODB;

CREATE TABLE IF NOT EXISTS experiments
(
    id         INT PRIMARY KEY AUTO_INCREMENT,
    network_id INT                                 NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    FOREIGN KEY (network_id) REFERENCES networks (id)
) ENGINE = INNODB;

CREATE TABLE IF NOT EXISTS backup_pairs
(
    experiment_id  INT,
    name           VARCHAR(255),
    data_size_byte BIGINT                              NOT NULL,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    PRIMARY KEY (experiment_id, name),
    FOREIGN KEY (experiment_id) REFERENCES experiments (id)
) ENGINE = INNODB;

CREATE TABLE IF NOT EXISTS benchmarks
(
    experiment_id           INT,
    backup_pair_name        VARCHAR(255),
    received_data_size_byte BIGINT                              NOT NULL,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    PRIMARY KEY (experiment_id, backup_pair_name),
    FOREIGN KEY (experiment_id, backup_pair_name) REFERENCES backup_pairs (experiment_id, name)
) ENGINE = INNODB;