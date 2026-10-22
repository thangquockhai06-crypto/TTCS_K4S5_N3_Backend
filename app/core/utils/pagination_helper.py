def paginate(query, skip: int = 0, limit: int = 50):
    return query.offset(skip).limit(limit)
