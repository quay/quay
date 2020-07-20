package redis

// Fields returns a list of strings representing the fields in this field group
func (fg *RedisFieldGroup) Fields() []string {
	return []string{"BUILDLOGS_REDIS", "USER_EVENTS_REDIS"}
}
