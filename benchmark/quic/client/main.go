package main

import (
	"context"
	"crypto/tls"
	"flag"
	"fmt"
	"io"
	"log"
	"os"

	"github.com/lucas-clemente/quic-go"
)

var (
	addr string
	file string
)

func init() {
	flag.StringVar(&addr, "addr", "localhost:44300", "server address")
	flag.StringVar(&file, "file", "1K.txt", "file to send")
	flag.Parse()
}

func main() {
	w, err := os.Create("keylog.txt")
	if err != nil {
		panic(err)
	}

	session, err := quic.DialAddr(addr, genTLSConf(w), nil)
	if err != nil {
		log.Fatalln(err)
	}

	stream, err := session.OpenStreamSync(context.Background())
	if err != nil {
		log.Fatalln(err)
	}
	defer stream.Close()

	file, err := os.Open(fmt.Sprintf("client/chunk/%s", file))
	if err != nil {
		log.Fatalln(err)
	}
	defer file.Close()

	fmt.Println("sending data...")
	buf := make([]byte, 1024)
	var offset int64 = 0
	for {
		nr, errRead := file.ReadAt(buf, offset)
		if err != nil && err != io.EOF {
			log.Fatalln(err)
		}

		offset += int64(nr)
		if _, err = stream.Write(buf[:nr]); err != nil {
			log.Fatalln(err)
		}

		if errRead == io.EOF {
			break
		}
	}
	fmt.Println("done")

	received, err := io.ReadAll(stream)
	if err != nil {
		log.Fatalln(err)
	}
	fmt.Printf("received: '%s'\n", received)
}

func genTLSConf(w io.Writer) *tls.Config {
	return &tls.Config{
		InsecureSkipVerify: true,
		NextProtos:         []string{"quic-echo-example"},
		KeyLogWriter:       w,
	}
}
