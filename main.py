import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pymongo import MongoClient
from motor.motor_asyncio import AsyncIOMotorClient

# Create the FastAPI app
app = FastAPI()

# Establish a connection to MongoDB
client = MongoClient('mongodb://localhost:27017')
db = client['bookstore']
collection = db['books']

# Create the Pydantic model for the book data
class Book(BaseModel):
    title: str
    author: str
    description: str
    price: float
    stock: int
    sold: int = 0


# Create the API endpoints

@app.get("/books")
async def get_books():
    # Get all the books from the database
    books = await collection.find().to_list(length=None)
    return books

@app.get("/books/{book_id}")
async def get_book(book_id: int):
    # Get the book with the specified ID from the database
    book = await collection.find_one({"_id": book_id})
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return book

@app.post("/books")
async def add_book(book: Book):
    # Validate the book data
    if not book.validate():
        raise HTTPException(status_code=400, detail="Invalid book data")

    # Add the book to the database
    await collection.insert_one(book.dict())
    return book

@app.put("/books/{book_id}")
async def update_book(book_id: int, book: Book):
    # Get the book with the specified ID from the database
    existing_book = await collection.find_one({"_id": book_id})
    if existing_book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    # Update the book in the database
    await collection.update_one({"_id": book_id}, {"$set": book.dict()})
    return book

@app.delete("/books/{book_id}")
async def delete_book(book_id: int):
    # Get the book with the specified ID from the database
    existing_book = await collection.find_one({"_id": book_id})
    if existing_book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    # Delete the book from the database
    await collection.delete_one({"_id": book_id})
    return None

@app.get("/search")
async def search_books(title: str, author: str, min_price: float, max_price: float):
    # Create a query object
    query = {
        "title": {"$regex": title},
        "author": {"$regex": author},
        "price": {"$gte": min_price, "$lte": max_price}
    }

    # Get the books that match the query
    books = await collection.find(query).to_list(length=None)
    return books

# Run the app
if __name__ == "__main__":
    app.run(debug=True)