package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"time"

	"github.com/TOMOFUMI-KONDO/disaster-resistant-network/benchmark"

	"github.com/lucas-clemente/quic-go"
)

const (
	ReadTimeout = time.Second * 10
	LogInterval = 1e6 // 1MB
)

var (
	addr    string
	verbose bool

	expId    int
	pairName string

	dbCfg = &benchmark.DBConfig{}

	total int64
)

func init() {
	flag.StringVar(&addr, "addr", ":44300", "server address")
	flag.BoolVar(&verbose, "v", false, "weather to show progress of data receiving")

	flag.IntVar(&expId, "exp", -1, "experiment id")
	flag.StringVar(&pairName, "pair", "", "name of backup host pair")

	flag.StringVar(&dbCfg.User, "dbuser", "root", "database user")
	flag.StringVar(&dbCfg.Pass, "dbpass", "", "database password")
	flag.StringVar(&dbCfg.Host, "dbhost", "127.0.0.1", "database host")
	flag.IntVar(&dbCfg.Port, "dbport", 3306, "database port")
	flag.StringVar(&dbCfg.Database, "dbdb", "", "database name")

	flag.Parse()
}

func main() {
	// make listener, specifying addr and tls config.
	// QUIC needs to be used with TLS.
	// see: https://www.rfc-editor.org/rfc/rfc9001.html
	listener, err := quic.ListenAddr(addr, benchmark.GenTLSConf(), nil)
	if err != nil {
		log.Fatalf("failed to listen addr: %v\n", err)
	}
	fmt.Printf("listening %s\n", addr)

	for {
		sess, err := listener.Accept(context.Background())
		if err != nil {
			log.Fatalf("failed to accept: %v\n", err)
		}
		go handleSess(sess)
	}
}

func handleSess(sess quic.Session) {
	defer func() {
		if err := benchmark.Record(expId, pairName, total, dbCfg); err != nil {
			log.Printf("failed to record benchmark: %v", err)
		}
	}()

	stream, err := sess.AcceptStream(context.Background())
	if err != nil {
		log.Printf("failed to accept stream: %v\n", err)
		return
	}
	defer stream.Close()

	var logAt int64
	buf := make([]byte, 1024)
	for {
		if err = stream.SetReadDeadline(time.Now().Add(ReadTimeout)); err != nil {
			log.Printf("failed to set read deadline: %v\n", err)
			return
		}

		nr, err := stream.Read(buf)
		if err != nil {
			log.Printf("failed to read: %v\n", err)
			return
		}

		total += int64(nr)
		if verbose && total > logAt+LogInterval {
			fmt.Printf("now %s...\n", benchmark.FormatSize(total))
			logAt = total
		}

		if nr < len(buf) {
			break
		}
	}

	fmt.Printf("done!\n")

	// tell received size
	if _, err = stream.Write([]byte(fmt.Sprintf("total %s", benchmark.FormatSize(total)))); err != nil {
		fmt.Printf("failed to write: %v\n", err)
	}
}
