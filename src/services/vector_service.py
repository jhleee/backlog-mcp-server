import os
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
import logging

from config.settings import settings

logger = logging.getLogger(__name__)


class VectorService:
    def __init__(self):
        self.client = None
        self.collection = None
        self.embedding_function = None
        self._initialize_chromadb()

    def _initialize_chromadb(self):
        """Initialize ChromaDB client and collection"""
        try:
            self.client = chromadb.PersistentClient(
                path=settings.chroma_persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )

            # Try to get existing collection first
            try:
                self.collection = self.client.get_collection(
                    name=settings.chroma_collection_name
                )
                logger.info(f"Using existing ChromaDB collection: {settings.chroma_collection_name}")
            except ValueError:
                # Collection doesn't exist, create new one
                if settings.openai_api_key:
                    self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
                        api_key=settings.openai_api_key,
                        model_name="text-embedding-ada-002"
                    )
                else:
                    self.embedding_function = embedding_functions.DefaultEmbeddingFunction()

                self.collection = self.client.create_collection(
                    name=settings.chroma_collection_name,
                    embedding_function=self.embedding_function
                )
                logger.info(f"Created new ChromaDB collection: {settings.chroma_collection_name}")

        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            # Try to reset and create new collection
            try:
                logger.info("Attempting to reset ChromaDB...")
                self.client.delete_collection(settings.chroma_collection_name)

                if settings.openai_api_key:
                    self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
                        api_key=settings.openai_api_key,
                        model_name="text-embedding-ada-002"
                    )
                else:
                    self.embedding_function = embedding_functions.DefaultEmbeddingFunction()

                self.collection = self.client.create_collection(
                    name=settings.chroma_collection_name,
                    embedding_function=self.embedding_function
                )
                logger.info(f"Reset and created new ChromaDB collection: {settings.chroma_collection_name}")
            except Exception as reset_error:
                logger.error(f"Failed to reset ChromaDB: {reset_error}")
                raise

    def add_document(self, document_id: str, text: str, metadata: Dict[str, Any]) -> None:
        """Add a document to the vector database"""
        try:
            # Filter out None values and ensure consistent types for ChromaDB
            filtered_metadata = {}
            for k, v in metadata.items():
                if v is not None:
                    # Convert all values to string to ensure consistency
                    if isinstance(v, (int, float)):
                        filtered_metadata[k] = str(v)
                    else:
                        filtered_metadata[k] = v

            self.collection.add(
                documents=[text],
                metadatas=[filtered_metadata],
                ids=[document_id]
            )
            logger.info(f"Added document {document_id} to vector database")
        except Exception as e:
            logger.error(f"Failed to add document {document_id}: {e}")
            raise

    def update_document(self, document_id: str, text: str, metadata: Dict[str, Any]) -> None:
        """Update a document in the vector database"""
        try:
            # Filter out None values and ensure consistent types for ChromaDB
            filtered_metadata = {}
            for k, v in metadata.items():
                if v is not None:
                    # Convert all values to string to ensure consistency
                    if isinstance(v, (int, float)):
                        filtered_metadata[k] = str(v)
                    else:
                        filtered_metadata[k] = v

            self.collection.update(
                documents=[text],
                metadatas=[filtered_metadata],
                ids=[document_id]
            )
            logger.info(f"Updated document {document_id} in vector database")
        except Exception as e:
            logger.error(f"Failed to update document {document_id}: {e}")
            raise

    def delete_document(self, document_id: str) -> None:
        """Delete a document from the vector database"""
        try:
            self.collection.delete(ids=[document_id])
            logger.info(f"Deleted document {document_id} from vector database")
        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {e}")
            raise

    def search(self, query: str, n_results: int = 5, filter: Optional[Dict] = None) -> Dict[str, Any]:
        """Search for similar documents"""
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=filter
            )

            formatted_results = []
            if results['ids'] and results['ids'][0]:
                for i in range(len(results['ids'][0])):
                    formatted_results.append({
                        'id': results['ids'][0][i],
                        'document': results['documents'][0][i] if results['documents'] else "",
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                        'distance': results['distances'][0][i] if results['distances'] else 0
                    })

            return {
                'query': query,
                'results': formatted_results,
                'count': len(formatted_results)
            }

        except Exception as e:
            logger.error(f"Search failed for query '{query}': {e}")
            return {'query': query, 'results': [], 'count': 0}

    def search_by_metadata(self, metadata_filter: Dict[str, Any], n_results: int = 10) -> List[Dict[str, Any]]:
        """Search documents by metadata filter"""
        try:
            results = self.collection.get(
                where=metadata_filter,
                limit=n_results
            )

            formatted_results = []
            if results['ids']:
                for i in range(len(results['ids'])):
                    formatted_results.append({
                        'id': results['ids'][i],
                        'document': results['documents'][i] if results['documents'] else "",
                        'metadata': results['metadatas'][i] if results['metadatas'] else {}
                    })

            return formatted_results

        except Exception as e:
            logger.error(f"Metadata search failed: {e}")
            return []

    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific document by ID"""
        try:
            results = self.collection.get(ids=[document_id])

            if results['ids']:
                return {
                    'id': results['ids'][0],
                    'document': results['documents'][0] if results['documents'] else "",
                    'metadata': results['metadatas'][0] if results['metadatas'] else {}
                }
            return None

        except Exception as e:
            logger.error(f"Failed to get document {document_id}: {e}")
            return None

    def get_all_documents(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all documents from the collection"""
        try:
            results = self.collection.get(limit=limit)

            formatted_results = []
            if results['ids']:
                for i in range(len(results['ids'])):
                    formatted_results.append({
                        'id': results['ids'][i],
                        'document': results['documents'][i] if results['documents'] else "",
                        'metadata': results['metadatas'][i] if results['metadatas'] else {}
                    })

            return formatted_results

        except Exception as e:
            logger.error(f"Failed to get all documents: {e}")
            return []

    def clear_collection(self) -> None:
        """Clear all documents from the collection"""
        try:
            self.client.delete_collection(settings.chroma_collection_name)
            self.collection = self.client.create_collection(
                name=settings.chroma_collection_name,
                embedding_function=self.embedding_function
            )
            logger.info("Collection cleared")
        except Exception as e:
            logger.error(f"Failed to clear collection: {e}")
            raise

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection"""
        try:
            count = self.collection.count()
            return {
                'collection_name': settings.chroma_collection_name,
                'document_count': count,
                'persist_directory': settings.chroma_persist_directory
            }
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {
                'collection_name': settings.chroma_collection_name,
                'document_count': 0,
                'error': str(e)
            }