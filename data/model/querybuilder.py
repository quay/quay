class QueryBuilder(object):
    def __init__(self, query):
        self.base_query = query
        self._base_query = query  # This field remains unchanged through all the operations

    def paginate(self, page_number, items_per_page):
        self.base_query = self.base_query.paginate(page_number, items_per_page)
        return self

    def sort(self, field, sort_type):
        if sort_type and sort_type == "desc":
            self.base_query = self.base_query.order_by(field.desc())
        else:
            # Default ordering type is Ascending so need not mention explicitly
            self.base_query = self.base_query.order_by(field)
        return self

    def count(self):
        return self._base_query.count()

    def execute(self):
        return self.base_query.execute()
