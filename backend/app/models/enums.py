from enum import StrEnum


class Category(StrEnum):
    FOOD = "Food"
    TRAVEL = "Travel"
    SHOPPING = "Shopping"
    BILLS = "Bills"
    EMI = "EMI"
    SUBSCRIPTIONS = "Subscriptions"
    SALARY = "Salary"
    RENT = "Rent"
    INVESTMENTS = "Investments"
    OTHER = "Other"


class TransactionType(StrEnum):
    CREDIT = "credit"
    DEBIT = "debit"


class SessionStatus(StrEnum):
    PENDING = "pending"
    PARSING = "parsing"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
