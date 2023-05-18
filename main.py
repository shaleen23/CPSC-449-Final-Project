from pydantic import BaseModel
import hashlib
from fastapi import FastAPI, HTTPException, Response
from typing import List, Optional
from bson import ObjectId
from pymongo import InsertOne, IndexModel
from motor.motor_asyncio import AsyncIOMotorClient


app = FastAPI()

# MongoDB connection setup
client = AsyncIOMotorClient("mongodb://localhost:27017")
db = client["bookstore"]
collection = db["books"]
collection.delete_many({}) #deletes records after each time it is executed

# Book model
class Book(BaseModel):
    book_id: Optional[str]
    title: str
    author: str
    description: str
    price: float
    stock: int
    sold_count: int = 0

    
def generate_book_id(title: str, author: str) -> str:
    """
    Generates a unique book ID based on the book's title and author.
    """
    book_id = f"{title}{author}".encode()
    book_id_hash = hashlib.md5(book_id).hexdigest()
    return book_id_hash



books_data = []



async def insert_books():
    """
    Inserts the initial set of books into the database.
    """
    operations = []
    for book_data in books_data:
        book_data["_id"] = book_data["book_id"]
        del book_data["book_id"]
        operations.append(InsertOne(book_data))
    await collection.bulk_write(operations)


async def create_indexes():
    """
    Creates indexes on the book collection for faster querying.
    """
    index_models = [
        IndexModel("title"),
        IndexModel("author"),
        IndexModel("price"),
        IndexModel("sold_count")
    ]
    await collection.create_indexes(index_models)



@app.get("/books", response_model=List[Book])
async def get_books(response: Response):
    """
    Retrieves all books from the database.
    """
    books = await collection.find().to_list(1000)
    formatted_books = [{**book, "book_id": str(book["_id"])} for book in books]
    response.headers["X-Total-Count"] = str(len(formatted_books))
    return formatted_books





@app.get("/books/{book_id}", response_model=Book)
async def get_book(book_id: str):
    """
    Retrieves a specific book from the database by its book ID.
    """
    book = await collection.find_one({"_id": ObjectId(book_id)})
    if book:
        return {**book, "book_id": str(book["_id"])}
    else:
        raise HTTPException(status_code=404, detail="Book not found")




@app.post("/books")
async def add_book(book: Book):
    # Convert book object to dictionary
    book_dict = book.dict()

    # Extract book_id from the dictionary
    book_id = book_dict.get("id")

    # Check if a book with the same ID already exists
    existing_book = await collection.find_one({"_id": ObjectId(book_id)})
    if existing_book:
        raise HTTPException(status_code=400, detail="Book with the same ID already exists")

    # Insert the book into the collection
    inserted_book = await collection.insert_one(book_dict)

    # Get the inserted book's ID
    book_id = str(inserted_book.inserted_id)

    return {"message": "Book added successfully", "book_id": book_id}



@app.put("/books/{book_id}")
async def update_book(book_id: str, book: Book):
    """
    Updates a book in the database.
    """
    book_data = book.dict(exclude_unset=True)
    result = await collection.update_one({"_id": ObjectId(book_id)}, {"$set": book_data})
    
    if result.matched_count > 0:
        if result.modified_count > 0:
            return {"message": "Book updated successfully"}
        else:
            return {"message": "Book already up to date"}
    else:
        raise HTTPException(status_code=404, detail="Book not found")





@app.delete("/books/{book_id}")
async def delete_book(book_id: str):
    """
    Deletes a book from the database.
    """
    result = await collection.delete_one({"_id": ObjectId(book_id)})
    
    if result.deleted_count:
        return {"message": "Book deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="Book not found")




@app.get("/search", response_model=List[Book])
async def search_books(title: Optional[str] = None, author: Optional[str] = None, min_price: Optional[float] = None, max_price: Optional[float] = None):
    """
    Searches for books based on various criteria such as title, author, minimum price, and maximum price.
    """
    query = {}

    if title:
        query["title"] = {"$regex": f".*{title}.*", "$options": "i"}
    if author:
        query["author"] = {"$regex": f".*{author}.*", "$options": "i"}
    if min_price is not None:
        query["price"] = {"$gte": min_price} if "price" not in query else {"$gte": min_price, **query["price"]}
    if max_price is not None:
        query["price"] = {"$lte": max_price} if "price" not in query else {"$lte": max_price, **query["price"]}

    results = await collection.find(query).to_list(1000)
    return results



@app.post("/books/{book_id}/buy")
async def buy_book(book_id: str):
    """
    Buys a book if it is in stock.
    """
    updated_book = await collection.find_one_and_update(
        {"_id": ObjectId(book_id), "stock": {"$gt": 0}},
        {"$inc": {"stock": -1, "sold_count": 1}}
    )
    if updated_book:
        return {"message": "Book purchased successfully"}
    else:
        raise HTTPException(status_code=400, detail="Book is out of stock")


# Run the application
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
