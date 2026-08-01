package cache

import (
	"testing"

	"github.com/quay/quay/config-tool/pkg/lib/shared"
)

// TestValidateCache checks that Validate returns proper values

func TestValidateCache(t *testing.T) {
	var tests = []struct {
		name   string
		config map[string]any
		want   string
	}{
		{
			name: "Cache_Test_Wrong_Engine_Type",
			config: map[string]any{
				"DATA_MODEL_CACHE_CONFIG": map[string]any{
					"engine":                    "unsupported",
					"repository_blob_cache_ttl": "60s",
				},
			},
			want: "typeError",
		},
		{
			name: "Cache_Test_Correct_Engine_Type",
			config: map[string]any{
				"DATA_MODEL_CACHE_CONFIG": map[string]any{
					"engine": "inmemory",
				},
			},
			want: "valid",
		},
		{
			name: "Cache_Test_Too_Large_Cache_Size",
			config: map[string]any{
				"DATA_MODEL_CACHE_CONFIG": map[string]any{
					"engine":           "inmemory",
					"value_size_limit": "123GiB",
				},
			},
			want: "invalid",
		},
		{
			name: "Cache_Test_Redis_Port_Out_Of_Bounds",
			config: map[string]any{
				"DATA_MODEL_CACHE_CONFIG": map[string]any{
					"engine": "redis",
					"redis_config": map[string]any{
						"primary": map[string]any{
							"host": "localhost",
							"port": 654321,
							"ssl":  true,
						},
					},
				},
			},
			want: "typeError",
		},
		{
			name: "Cache_Test_Redis_Primary_Valid_Secondary_Invalid",
			config: map[string]any{
				"DATA_MODEL_CACHE_CONFIG": map[string]any{
					"engine": "redis",
					"redis_config": map[string]any{
						"primary": map[string]any{
							"host": "localhost",
							"port": 1234,
						},
						"replica": map[string]any{
							"host": "someotherhost",
							"port": 123456,
						},
					},
				},
			},
			want: "typeError",
		},
		{
			name: "Cache_Test_Memcached_Valid_Config",
			config: map[string]any{
				"DATA_MODEL_CACHE_CONFIG": map[string]any{
					"engine": "memcached",
					"endpoint": []any{
						"localhost",
						12345,
					},
					"repository_blob_cache_ttl":  "60s",
					"catalog_page_cache_ttl":     "60s",
					"active_repo_tags_cache_ttl": "60s",
					"value_size_limit":           "2MiB",
				},
			},
			want: "valid",
		},
		{
			name: "Cache_Test_Rediscluster_Multiple_Nodes",
			config: map[string]any{
				"DATA_MODEL_CACHE_CONFIG": map[string]any{
					"engine": "rediscluster",
					"redis_config": map[string]any{
						"startup_nodes": []map[string]any{
							{
								"host": "localhost",
								"port": 1234,
							},
							{
								"host": "someotherhost",
								"port": 5432,
							},
						},
						"read_from_replica": true,
					},
				},
			},
			want: "valid",
		},
		{
			name: "Cache_Test_Invalid_TTL_Pattern",
			config: map[string]any{
				"DATA_MODEL_CACHE_CONFIG": map[string]any{
					"engine":                    "inmemory",
					"repository_blob_cache_ttl": "someinvalidvalue123456",
				},
			},
			want: "invalid",
		},
		{
			name:   "Cache_Test_Absent_Model_Cache",
			config: map[string]any{},
			want:   "valid",
		},
		{
			name: "Cache_Test_Missing_Redis_Config",
			config: map[string]any{
				"DATA_MODEL_CACHE_CONFIG": map[string]any{
					"engine": "redis",
				},
			},
			want: "typeError",
		},
		{
			name: "Cache_Test_Missing_Endpoint_When_Engine_Memcached",
			config: map[string]any{
				"DATA_MODEL_CACHE_CONFIG": map[string]any{
					"engine":                    "memcached",
					"repository_blob_cache_ttl": "60s",
				},
			},
			want: "typeError",
		},
		{
			name: "Cache_Test_Too_Large_Cache_Size",
			config: map[string]any{
				"DATA_MODEL_CACHE_CONFIG": map[string]any{
					"engine":           "inmemory",
					"value_size_limit": "512MiB",
				},
			},
			want: "invalid",
		},
		{
			name: "Cache_Size_Malformed_Entry",
			config: map[string]any{
				"DATA_MODEL_CACHE_CONFIG": map[string]any{
					"engine":           "inmemory",
					"value_size_limit": "wrongvalue",
				},
			},
			want: "invalid",
		},
		{
			name: "Cache_Size_Correct_Value",
			config: map[string]any{
				"DATA_MODEL_CACHE_CONFIG": map[string]any{
					"engine":           "inmemory",
					"value_size_limit": "7MiB",
				},
			},
			want: "valid",
		},
		{
			name: "Cache_Size_Set_In_KiB",
			config: map[string]any{
				"DATA_MODEL_CACHE_CONFIG": map[string]any{
					"engine":           "inmemory",
					"value_size_limit": "2048KiB",
				},
			},
			want: "invalid",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			fg, err := NewCacheFieldGroup(tt.config)
			if err != nil {
				if tt.want != "typeError" {
					t.Errorf("Expected %s, received constructor error: %s", tt.want, err.Error())
				}
				return
			}

			if tt.want == "typeError" {
				t.Errorf("Expected constructor error, but got none")
				return
			}

			opts := shared.Options{
				Mode: "testing",
			}

			validationErrors := fg.Validate(opts)

			received := ""
			if len(validationErrors) == 0 {
				received = "valid"
			} else {
				received = "invalid"
			}

			if tt.want != received {
				t.Errorf("Expected %s, received %s", tt.want, received)
				for _, ve := range validationErrors {
					t.Logf("validation error: %s", ve.Message)
				}
			}
		})
	}
}
