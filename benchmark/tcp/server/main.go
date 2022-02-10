package main

import (
	"crypto/tls"
	"flag"
	"fmt"
	"log"
	"net"
	"time"

	"github.com/TOMOFUMI-KONDO/disaster-resistant-network/benchmark"
)

const ReadTimeout = time.Second * 10

var (
	addr    string
	verbose bool
	total   int64
)

func init() {
	flag.StringVar(&addr, "addr", ":44300", "server address")
	flag.BoolVar(&verbose, "v", false, "weather to show progress of data receiving")
	flag.Parse()
}

func main() {
	listener, err := tls.Listen("tcp", addr, benchmark.GenTLSConf())
	if err != nil {
		fmt.Printf("failed to listen: %v\n", err)
	}
	fmt.Printf("listening %s\n", addr)

	for {
		sess, err := listener.Accept()
		if err != nil {
			log.Fatalf("failed to accept: %v\n", err)
		}
		go handleConn(sess)
	}
}

func handleConn(conn net.Conn) {
	defer conn.Close()

	buf := make([]byte, 1024)
	for {
		if err := conn.SetReadDeadline(time.Now().Add(ReadTimeout)); err != nil {
			log.Printf("failed to set read deadline: %v\n", err)
			return
		}

		nr, err := conn.Read(buf)
		if err != nil {
			log.Printf("failed to read: %v\n", err)
			return
		}

		total += int64(nr)
		if verbose {
			fmt.Printf("now %s...\n", benchmark.FormatSize(total))
		}

		if nr < len(buf) {
			break
		}
	}

	fmt.Printf("done!\ntotal %dbyte\n", total)

	// tell received size
	if _, err := conn.Write([]byte(fmt.Sprintf("total %s", benchmark.FormatSize(total)))); err != nil {
		fmt.Printf("failed to write: %v\n", err)
	}
}
