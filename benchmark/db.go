package benchmark

import (
	"database/sql"
	"fmt"
	"time"

	_ "github.com/go-sql-driver/mysql"
)

type DBConfig struct {
	User     string
	Pass     string
	Host     string
	Port     int
	Database string
}

func Record(expId int, pairName string, rcvSize int64, cfg *DBConfig) error {
	fmt.Printf("expId:%d pairName:%s rcvSize:%s\n", expId, pairName, FormatSize(rcvSize))

	db, err := sql.Open("mysql", fmt.Sprintf("%s:%s@tcp(%s:%d)/%s", cfg.User, cfg.Pass, cfg.Host, cfg.Port, cfg.Database))
	if err != nil {
		return fmt.Errorf("failed to open db: %w", err)
	}
	defer db.Close()

	db.SetConnMaxLifetime(time.Minute * 3)
	db.SetMaxOpenConns(10)
	db.SetMaxIdleConns(10)

	stmt, err := db.Prepare(`insert into benchmarks (experiment_id, backup_pair_name, received_data_size_byte) values(?, ?, ?) 
on duplicate key update received_data_size_byte = ?`)
	if err != nil {
		return fmt.Errorf("failed to prepare statement: %w", err)
	}
	defer stmt.Close()
	if _, err = stmt.Exec(expId, pairName, rcvSize, rcvSize); err != nil {
		return fmt.Errorf("failed to exec insert: %w", err)
	}

	return nil
}
