package clairv4

import (
	"bytes"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"net/url"
	"regexp"
	"strconv"
	"strings"
	"time"

	"github.com/golang-jwt/jwt/v5"

	"github.com/quay/go-secscan/models"
)

const (
	defaultRequestTimeout = 30 * time.Second
	indexRequestTimeout   = 10 * time.Minute
)

type Client struct {
	Endpoint   string
	HTTP       *http.Client
	jwtPSK     []byte
	maxLayerSz int64
}

func New(endpoint string, httpClient *http.Client, jwtPSKBase64 string) (*Client, error) {
	if endpoint == "" {
		return nil, errors.New("endpoint required")
	}
	if httpClient == nil {
		httpClient = &http.Client{Timeout: defaultRequestTimeout}
	}
	var key []byte
	if jwtPSKBase64 != "" {
		b, err := base64.StdEncoding.DecodeString(jwtPSKBase64)
		if err != nil {
			return nil, fmt.Errorf("decode psk: %w", err)
		}
		key = b
	}
	return &Client{Endpoint: strings.TrimRight(endpoint, "/"), HTTP: httpClient, jwtPSK: key}, nil
}

func (c *Client) WithMaxLayerSize(max string) *Client {
	c.maxLayerSz = parseSize(max)
	return c
}

// parseSize mirrors Python's _layer_size_str_to_bytes: N + unit where unit in {B,K,M,G,T}
func parseSize(s string) int64 {
	s = strings.TrimSpace(s)
	if s == "" {
		return 0
	}
	re := regexp.MustCompile(`(?i)^(\d+)([BKMG T])$`)
	s = strings.ReplaceAll(s, " ", "")
	m := re.FindStringSubmatch(s)
	if len(m) != 3 {
		return 0
	}
	n, err := strconv.ParseInt(m[1], 10, 64)
	if err != nil {
		return 0
	}
	switch strings.ToUpper(m[2]) {
	case "B":
		return n
	case "K":
		return n << 10
	case "M":
		return n << 20
	case "G":
		return n << 30
	case "T":
		return n << 40
	default:
		return 0
	}
}

func (c *Client) State() (map[string]string, error) {
	var out map[string]string
	if err := c.doJSON(http.MethodGet, "/indexer/api/v1/index_state", nil, indexRequestTimeout, &out); err != nil {
		return nil, err
	}
	return out, nil
}

// BuildLayer constructs a Clair layer payload entry and enforces optional max size.
func (c *Client) BuildLayer(hash, uri string, headers map[string][]string, compressedSize int64) (map[string]any, error) {
	if c.maxLayerSz > 0 && compressedSize > c.maxLayerSz {
		return nil, fmt.Errorf("layer too large: %d > %d", compressedSize, c.maxLayerSz)
	}
	return map[string]any{
		"hash":            hash,
		"uri":             uri,
		"headers":         headers,
		"compressed_size": compressedSize,
	}, nil
}

func (c *Client) Index(manifestHash string, layers []map[string]any) (models.IndexReport, string, error) {
	// Enforce max layer size if configured, similar to Python's index()
	if c.maxLayerSz > 0 {
		for _, l := range layers {
			if v, ok := l["compressed_size"]; ok {
				switch sz := v.(type) {
				case int64:
					if sz > c.maxLayerSz {
						return models.IndexReport{}, "", fmt.Errorf("layer too large: %d > %d", sz, c.maxLayerSz)
					}
				case int:
					if int64(sz) > c.maxLayerSz {
						return models.IndexReport{}, "", fmt.Errorf("layer too large: %d > %d", sz, c.maxLayerSz)
					}
				case float64:
					if int64(sz) > c.maxLayerSz {
						return models.IndexReport{}, "", fmt.Errorf("layer too large: %d > %d", int64(sz), c.maxLayerSz)
					}
				}
			}
		}
	}
	body := map[string]any{
		"hash":   manifestHash,
		"layers": layers,
	}
	var rep models.IndexReport
	hdr, err := c.doJSONWithHeaders(http.MethodPost, "/indexer/api/v1/index_report", body, indexRequestTimeout, &rep)
	if err != nil {
		return models.IndexReport{}, "", err
	}
	etag := strings.Trim(hdr.Get("Etag"), "\"")
	return rep, etag, nil
}

func (c *Client) IndexReport(manifestHash string) (models.IndexReport, error) {
	var rep models.IndexReport
	path := "/indexer/api/v1/index_report/" + url.PathEscape(manifestHash)
	if err := c.doJSON(http.MethodGet, path, nil, indexRequestTimeout, &rep); err != nil {
		return models.IndexReport{}, err
	}
	return rep, nil
}

func (c *Client) VulnerabilityReport(manifestHash string) (models.VulnerabilityReport, error) {
	var rep models.VulnerabilityReport
	path := "/matcher/api/v1/vulnerability_report/" + url.PathEscape(manifestHash)
	if err := c.doJSON(http.MethodGet, path, nil, defaultRequestTimeout, &rep); err != nil {
		return models.VulnerabilityReport{}, err
	}
	return rep, nil
}

func (c *Client) RetrieveNotificationPage(notificationID, next string) (models.NotificationPage, error) {
	var rep models.NotificationPage
	query := ""
	if next != "" {
		query = "?next=" + url.QueryEscape(next)
	}
	path := "/notifier/api/v1/notification/" + url.PathEscape(notificationID) + query
	if err := c.doJSON(http.MethodGet, path, nil, defaultRequestTimeout, &rep); err != nil {
		return models.NotificationPage{}, err
	}
	return rep, nil
}

func (c *Client) DeleteNotification(notificationID string) error {
	path := "/notifier/api/v1/notification/" + url.PathEscape(notificationID)
	_, err := c.do(http.MethodDelete, path, nil, defaultRequestTimeout, nil)
	return err
}

func (c *Client) DeleteIndexReport(manifestHash string) error {
	path := "/indexer/api/v1/index_report/" + url.PathEscape(manifestHash)
	_, err := c.do(http.MethodDelete, path, nil, indexRequestTimeout, nil)
	return err
}

func (c *Client) signJWT() (string, error) {
	if len(c.jwtPSK) == 0 {
		return "", nil
	}
	claims := jwt.MapClaims{
		"iss": "quay",
		"exp": time.Now().Add(5 * time.Minute).Unix(),
	}
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	return token.SignedString(c.jwtPSK)
}

func (c *Client) doJSON(method, path string, body any, timeout time.Duration, out any) error {
	_, err := c.doJSONWithHeaders(method, path, body, timeout, out)
	return err
}

func (c *Client) doJSONWithHeaders(method, path string, body any, timeout time.Duration, out any) (http.Header, error) {
	var b []byte
	var err error
	if body != nil {
		b, err = json.Marshal(body)
		if err != nil {
			return nil, err
		}
	}
	h := make(http.Header)
	h.Set("Content-Type", "application/json")
	if tok, _ := c.signJWT(); tok != "" {
		h.Set("Authorization", "Bearer "+tok)
	}

	resp, err := c.do(method, path, bytes.NewReader(b), timeout, h)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if out != nil {
		if err := json.NewDecoder(resp.Body).Decode(out); err != nil {
			return nil, err
		}
	}
	return resp.Header, nil
}

func (c *Client) do(method, path string, body *bytes.Reader, timeout time.Duration, headers http.Header) (*http.Response, error) {
	req, err := http.NewRequest(method, c.Endpoint+path, body)
	if err != nil {
		return nil, err
	}
	if headers != nil {
		req.Header = headers
	}
	client := c.HTTP
	if timeout > 0 {
		client = &http.Client{Timeout: timeout}
	}
	resp, err := client.Do(req)
	if err != nil {
		return nil, err
	}
	if resp.StatusCode >= 400 {
		defer resp.Body.Close()
		return nil, fmt.Errorf("upstream status %d", resp.StatusCode)
	}
	return resp, nil
}
