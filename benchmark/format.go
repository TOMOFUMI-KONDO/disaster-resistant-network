package benchmark

import (
	"fmt"
)

func FormatSize(size int64) string {
	var k int64 = 1e3
	if size < k {
		return fmt.Sprintf("%dB", size)
	}

	var m int64 = 1e6
	if size < m {
		return fmt.Sprintf("%dKB", size/k)
	}

	var g int64 = 1e9
	if size < g {
		return fmt.Sprintf("%dMB", size/m)
	}

	return fmt.Sprintf("%dGB", size/g)
}
