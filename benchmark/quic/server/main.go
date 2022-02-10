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

const ReadTimeout = time.Second * 10

var (
	addr    string
	verbose bool
	total   int
)

func init() {
	flag.StringVar(&addr, "addr", ":44300", "server address")
	flag.BoolVar(&verbose, "v", false, "weather to show progress of data receiving")
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
			log.Fatalln(err)
		}
		go handleSess(sess)
	}
}

func handleSess(sess quic.Session) {
	stream, err := sess.AcceptStream(context.Background())
	if err != nil {
		log.Println(err)
		return
	}
	defer stream.Close()

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

		total += nr
		if verbose {
			fmt.Printf("now %dbyte...\n", total)
		}

		if nr < len(buf) {
			break
		}
	}

	fmt.Printf("done!\ntotal %dbyte\n", total)

	// tell received size
	if _, err = stream.Write([]byte(fmt.Sprintf("total %dbyte", total))); err != nil {
		fmt.Printf("failed to write: %v\n", err)
	}
}
