package benchmark

import (
	"fmt"
	"math"
)

func FormatSize(size int64) string {
	k := int64(math.Pow(2, 10))
	if size < k {
		return fmt.Sprintf("%dB", size)
	}

	m := int64(math.Pow(2, 20))
	if size < m {
		return fmt.Sprintf("%dKB", size/k)
	}

	g := int64(math.Pow(2, 30))
	if size < g {
		return fmt.Sprintf("%dMB", size/m)
	}

	return fmt.Sprintf("%dGB", size/g)
}
