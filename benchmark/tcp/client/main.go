package main

import (
	"crypto/tls"
	"flag"
	"fmt"
	"io"
	"log"
	"os"
	"time"
)

const (
	RetryInterval = time.Second * 3
	WriteTimeout  = time.Second * 5
)

var (
	addr   string
	chunk  string
	offset int64
)

func init() {
	flag.StringVar(&addr, "addr", "localhost:44300", "server address")
	flag.StringVar(&chunk, "chunk", "1K.txt", "chunk file to send")
	flag.Parse()
}

func main() {
	w, err := os.Create("keylog.txt")
	if err != nil {
		log.Fatalf("failed to create keylog.txt: %v\n", err)
	}

	for {
		conn, err := tls.Dial("tcp", addr, genTLSConf(w))
		if err != nil {
			log.Printf("failed to dial: %v\nretrying...\n", err)
			time.Sleep(RetryInterval)
			continue
		}

		if err = send(conn, &offset); err != nil {
			log.Printf("failed to send: %v\nretrying...\n", err)
			time.Sleep(RetryInterval)
			continue
		}

		break
	}
}

func send(conn *tls.Conn, offset *int64) error {
	defer conn.Close()

	file, err := os.Open(fmt.Sprintf("chunk/%s", chunk))
	if err != nil {
		return err
	}
	defer file.Close()

	buf := make([]byte, 1024)

	fmt.Println("sending data...")
	for {
		nr, err := file.ReadAt(buf, *offset)
		var fin bool
		if err == io.EOF {
			fin = true
		} else if err != nil {
			return err
		}

		if err = conn.SetWriteDeadline(time.Now().Add(WriteTimeout)); err != nil {
			return err
		}

		nw, err := conn.Write(buf[:nr])
		*offset += int64(nw)
		if err != nil {
			return err
		}

		if fin {
			break
		}
	}
	fmt.Println("done!")

	// notify finish
	if _, err := conn.Write([]byte("fin")); err != nil {
		return err
	}

	received, err := io.ReadAll(conn)
	if err != nil {
		return err
	}
	fmt.Printf("received: '%s'\n", received)

	return nil
}

func genTLSConf(w io.Writer) *tls.Config {
	return &tls.Config{
		InsecureSkipVerify: true,
		NextProtos:         []string{"benchmark"},
		KeyLogWriter:       w,
	}
}
