# hmph

**hmph** is a bastardized ORM-like object management system
for database modules that conform to the DB-API.

Please do not use this in any serious project (or do, 
I'm not your mom)

```python
import hmph
from dataclasses import dataclass
import sqlite3

@dataclass
class Post(hmph.Model):
    class Meta:
        table_name = 'posts'
        primary_key = 'slug'

    slug: str
    title: str
    content: str

db = sqlite3.connect(":memory:")

# This library does not handle creating tables for your models yet.
# It might do it in the future, though, who knows.
db.execute("create table posts (slug text primary key, title text, content text)")

with db:
    cur = db.cursor()
    post = Post('my-post', 'My post', 'Test content')
    post.save(cur)
    post2 = Post.find(cur, 'my-post')
    if post.slug == post2.slug:
        print("yippee")
    else:
        print("ough")
```