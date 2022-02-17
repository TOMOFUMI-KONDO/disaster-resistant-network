package benchmark

import (
	"fmt"
	"io/ioutil"
	"os"
)

func GenChunk(chunk int64) (*os.File, error) {
	file, err := ioutil.TempFile("", "")
	if err != nil {
		return nil, fmt.Errorf("failed to create temp file: %w", err)
	}

	if err := file.Truncate(chunk); err != nil {
		return nil, fmt.Errorf("failed to truncate file: %w", err)
	}

	return file, nil
}
