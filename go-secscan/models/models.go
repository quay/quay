package models

import (
	"strconv"
)

// Basic types to mirror Python secscan structures
type IndexReport struct {
	ManifestHash string `json:"manifest_hash"`
	State        string `json:"state"`
	Err          string `json:"err"`
}

type Vulnerability struct {
	ID          string   `json:"id"`
	Name        string   `json:"name"`
	Description string   `json:"description"`
	Links       string   `json:"links"`
	FixedIn     string   `json:"fixed_in_version"`
	Severity    string   `json:"normalized_severity"`
	Package     string   `json:"package"`
	CVEs        []string `json:"cves"`
}

type VulnerabilityReport struct {
	ManifestHash           string                           `json:"manifest_hash"`
	Packages               map[string]Package               `json:"packages"`
	Environments           map[string][]Environment         `json:"environments"`
	Vulnerabilities        map[string]Vulnerability         `json:"vulnerabilities"`
	PackageVulnerabilities map[string][]string              `json:"package_vulnerabilities"`
	Enrichments            map[string][]map[string][]Enrich `json:"enrichments,omitempty"`
}

type Package struct {
	Name    string `json:"name"`
	Version string `json:"version"`
}

type Environment struct {
	IntroducedIn string `json:"introduced_in"`
}

type Enrich struct {
	BaseScore    float64 `json:"baseScore"`
	VectorString string  `json:"vectorString"`
}

// Notification types
type NotificationPage struct {
	Notifications []Notification `json:"notifications"`
	Page          *Page          `json:"page,omitempty"`
}

type Page struct {
	Next string `json:"next,omitempty"`
}

type Notification struct {
	ID            string        `json:"id"`
	Manifest      string        `json:"manifest"`
	Reason        string        `json:"reason"`
	Vulnerability Vulnerability `json:"vulnerability"`
}

// Storage interfaces
type Store interface {
	SaveIndexReport(IndexReport)
	GetIndexReport(string) (IndexReport, bool)
	DeleteIndexReport(string)
	SaveVulnReport(VulnerabilityReport)
	GetVulnReport(string) (VulnerabilityReport, bool)
	AddNotification(string, Notification)
	GetNotificationPage(string, string, int) (NotificationPage, bool)
	DeleteNotification(string)
}

// InMemoryStore implements Store for dev/testing
type InMemoryStore struct {
	IndexReports  map[string]IndexReport
	VulnReports   map[string]VulnerabilityReport
	Notifications map[string][]Notification
}

func NewInMemoryStore() *InMemoryStore {
	return &InMemoryStore{
		IndexReports:  make(map[string]IndexReport),
		VulnReports:   make(map[string]VulnerabilityReport),
		Notifications: make(map[string][]Notification),
	}
}

func (s *InMemoryStore) SaveIndexReport(r IndexReport) { s.IndexReports[r.ManifestHash] = r }
func (s *InMemoryStore) GetIndexReport(h string) (IndexReport, bool) {
	r, ok := s.IndexReports[h]
	return r, ok
}
func (s *InMemoryStore) DeleteIndexReport(h string)           { delete(s.IndexReports, h) }
func (s *InMemoryStore) SaveVulnReport(r VulnerabilityReport) { s.VulnReports[r.ManifestHash] = r }
func (s *InMemoryStore) GetVulnReport(h string) (VulnerabilityReport, bool) {
	r, ok := s.VulnReports[h]
	return r, ok
}
func (s *InMemoryStore) AddNotification(id string, n Notification) {
	s.Notifications[id] = append(s.Notifications[id], n)
}

// GetNotificationPage returns a page for a notification ID. `next` is the starting index as a decimal string.
func (s *InMemoryStore) GetNotificationPage(id, next string, pageSize int) (NotificationPage, bool) {
	ns, ok := s.Notifications[id]
	if !ok {
		return NotificationPage{}, false
	}
	start := 0
	if next != "" {
		if idx, err := strconv.Atoi(next); err == nil && idx >= 0 && idx < len(ns) {
			start = idx
		}
	}
	end := len(ns)
	if pageSize > 0 && start+pageSize < end {
		end = start + pageSize
	}
	var page *Page
	if end < len(ns) {
		page = &Page{Next: strconv.Itoa(end)}
	}
	return NotificationPage{Notifications: ns[start:end], Page: page}, true
}

func (s *InMemoryStore) DeleteNotification(id string) { delete(s.Notifications, id) }
