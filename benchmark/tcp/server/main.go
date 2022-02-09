package main

import (
	"crypto/rand"
	"crypto/rsa"
	"crypto/tls"
	"crypto/x509"
	"encoding/pem"
	"flag"
	"fmt"
	"log"
	"math/big"
	"net"
	"time"
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
	listener, err := tls.Listen("tcp", addr, genTLSConf())
	if err != nil {
		fmt.Printf("failed to listen: %v\n", err)
	}
	fmt.Printf("listening %s\n", addr)

	for {
		sess, err := listener.Accept()
		if err != nil {
			log.Fatalln(err)
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
	if _, err := conn.Write([]byte(fmt.Sprintf("total %dbyte", total))); err != nil {
		fmt.Printf("failed to write: %v\n", err)
	}
}

func genTLSConf() *tls.Config {
	key, err := rsa.GenerateKey(rand.Reader, 4096)
	if err != nil {
		panic(err)
	}
	template := x509.Certificate{SerialNumber: big.NewInt(1)}
	certDER, err := x509.CreateCertificate(rand.Reader, &template, &template, &key.PublicKey, key)
	if err != nil {
		panic(err)
	}
	keyPEM := pem.EncodeToMemory(&pem.Block{Type: "RSA PRIVATE KEY", Bytes: x509.MarshalPKCS1PrivateKey(key)})
	certPEM := pem.EncodeToMemory(&pem.Block{Type: "CERTIFICATE", Bytes: certDER})

	tlsCert, err := tls.X509KeyPair(certPEM, keyPEM)
	if err != nil {
		panic(err)
	}

	return &tls.Config{
		Certificates: []tls.Certificate{tlsCert},
		NextProtos:   []string{"benchmark"},
	}
}
