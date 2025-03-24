from fastapi import Request, HTTPException
from sqlalchemy.exc import NoResultFound, MultipleResultsFound, IntegrityError

def register_exception_handlers(app):
    @app.exception_handler(NoResultFound)
    async def no_result_found_handler(request: Request, exc: NoResultFound):
        raise HTTPException(status_code=404, detail="Resource not found")

    @app.exception_handler(MultipleResultsFound)
    async def multiple_results_handler(request: Request, exc: MultipleResultsFound):
        raise HTTPException(status_code=400, detail="Multiple records found when only one was expected")

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError):
        if "duplicate key" in str(exc.orig) or "UNIQUE constraint failed" in str(exc.orig):
            raise HTTPException(status_code=409, detail="Record already exists")

        raise HTTPException(status_code=409, detail="Database integrity error")
