package inference

import (
	"bytes"
	"encoding/base64"
	"fmt"
	"image"
	"image/color"
	"image/draw"
	_ "image/gif"
	"image/jpeg"
	_ "image/png"
	"strings"
)

const (
	videoReferenceMaxDecodedBytes = 20 << 20
	videoReferenceMaxPixels       = 40_000_000
	// media_jobs.input_json is limited to 1 MiB. Leave room for JSON framing and
	// future metadata so an inline image can be persisted safely before dispatch.
	videoReferenceMaxDataURILength = 900 << 10
)

func prepareVideoReferenceURLs(values []string) ([]string, error) {
	prepared := append([]string(nil), values...)
	for index, value := range prepared {
		value = strings.TrimSpace(value)
		if !strings.HasPrefix(strings.ToLower(value), "data:") {
			prepared[index] = value
			continue
		}
		normalized, err := normalizeVideoDataURI(value)
		if err != nil {
			return nil, fmt.Errorf("image.url 中的内嵌图片无效: %w", err)
		}
		prepared[index] = normalized
	}
	return prepared, nil
}

func normalizeVideoDataURI(value string) (string, error) {
	comma := strings.IndexByte(value, ',')
	if comma <= len("data:") {
		return "", fmt.Errorf("data URI 格式错误")
	}
	metadata := strings.Split(value[len("data:"):comma], ";")
	if len(metadata) < 2 || !strings.HasPrefix(strings.ToLower(strings.TrimSpace(metadata[0])), "image/") {
		return "", fmt.Errorf("data URI 必须是图片")
	}
	base64Encoded := false
	for _, parameter := range metadata[1:] {
		if strings.EqualFold(strings.TrimSpace(parameter), "base64") {
			base64Encoded = true
			break
		}
	}
	if !base64Encoded {
		return "", fmt.Errorf("data URI 必须使用 base64 编码")
	}

	encoded := strings.TrimSpace(value[comma+1:])
	if encoded == "" || int64(base64.StdEncoding.DecodedLen(len(encoded))) > videoReferenceMaxDecodedBytes {
		return "", fmt.Errorf("图片为空或超过 20 MiB")
	}
	raw, err := base64.StdEncoding.DecodeString(encoded)
	if err != nil {
		raw, err = base64.RawStdEncoding.DecodeString(encoded)
	}
	if err != nil || len(raw) == 0 || len(raw) > videoReferenceMaxDecodedBytes {
		return "", fmt.Errorf("图片 base64 数据无效或超过 20 MiB")
	}

	source, _, err := image.Decode(bytes.NewReader(raw))
	if err != nil {
		return "", fmt.Errorf("无法解码图片")
	}
	bounds := source.Bounds()
	if bounds.Dx() <= 0 || bounds.Dy() <= 0 || int64(bounds.Dx())*int64(bounds.Dy()) > videoReferenceMaxPixels {
		return "", fmt.Errorf("图片尺寸无效或像素数超过 4000 万")
	}

	canvasBounds := image.Rect(0, 0, bounds.Dx(), bounds.Dy())
	canvas := image.NewRGBA(canvasBounds)
	draw.Draw(canvas, canvasBounds, &image.Uniform{C: color.White}, image.Point{}, draw.Src)
	draw.Draw(canvas, canvasBounds, source, bounds.Min, draw.Over)
	for _, quality := range []int{85, 70, 55, 40, 25} {
		var output bytes.Buffer
		if err := jpeg.Encode(&output, canvas, &jpeg.Options{Quality: quality}); err != nil {
			return "", fmt.Errorf("图片转码失败")
		}
		dataURI := "data:image/jpeg;base64," + base64.StdEncoding.EncodeToString(output.Bytes())
		if len(dataURI) <= videoReferenceMaxDataURILength {
			return dataURI, nil
		}
	}
	return "", fmt.Errorf("图片压缩后仍超过视频任务的 900 KiB 安全上限")
}
