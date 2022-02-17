package main

import (
	"context"
	"crypto/tls"
	"flag"
	"fmt"
	"io"
	"log"
	"os"
	"time"

	"github.com/TOMOFUMI-KONDO/disaster-resistant-network/benchmark"

	"github.com/lucas-clemente/quic-go"
)

const (
	RetryInterval = time.Second * 3
	WriteTimeout  = time.Second * 5
)

var (
	addr   string
	chunk  int64
	offset int64
)

func init() {
	flag.StringVar(&addr, "addr", "localhost:44300", "server address")
	flag.Int64Var(&chunk, "chunk", 1e6, "size of chunk file to be sent")
	flag.Parse()
}

func main() {
	file, err := benchmark.GenChunk(chunk)
	if err != nil {
		log.Fatalf("failed to create chunk file: %v\n", err)
	}
	defer file.Close()

	w, err := os.Create("keylog.txt")
	if err != nil {
		log.Fatalf("failed to create keylog.txt: %v\n", err)
	}

	fmt.Printf("start to send %s chunk\n", benchmark.FormatSize(chunk))

	for {
		session, err := quic.DialAddr(addr, genTLSConf(w), nil)
		if err != nil {
			log.Printf("failed to dial addr: %v\nretrying...\n", err)
			time.Sleep(RetryInterval)
			continue
		}

		stream, err := session.OpenStreamSync(context.Background())
		if err != nil {
			log.Printf("failed to open stream sync: %v\nretrying...\n", err)
			time.Sleep(RetryInterval)
			continue
		}

		if err = send(stream, file, &offset); err != nil {
			log.Printf("failed to send: %v\nretrying...\n", err)
			time.Sleep(RetryInterval)
			continue
		}

		break
	}
}

func send(stream quic.Stream, file *os.File, offset *int64) error {
	defer stream.Close()

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

		if err = stream.SetWriteDeadline(time.Now().Add(WriteTimeout)); err != nil {
			return err
		}

		nw, err := stream.Write(buf[:nr])
		*offset += int64(nw)
		if err != nil {
			return err
		}

		if fin {
			break
		}
	}
	fmt.Println("done!")

	if _, err := stream.Write([]byte("fin")); err != nil {
		return err
	}

	received, err := io.ReadAll(stream)
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
