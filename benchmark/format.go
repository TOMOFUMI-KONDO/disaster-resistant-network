package benchmark

import (
	"fmt"
)

const (
	K int64 = 1e3
	M int64 = 1e6
	G int64 = 1e9
)

func FormatSize(size int64) string {
	if size < K {
		return fmt.Sprintf("%dB", size)
	}

	if size < M {
		k := size / K
		return fmt.Sprintf("%dKB %dB", k, size-k*K)
	}

	if size < G {
		m := size / M
		k := (size - m*M) / K
		return fmt.Sprintf("%dMB %dKB %dB", m, k, size-m*M-k*K)
	}

	g := size / G
	m := (size - g*G) / M
	k := (size - g*G - m*M) / K
	return fmt.Sprintf("%dGB %dMB %dKB %dB", g, m, k, size-g*G-m*M-k*K)
}
