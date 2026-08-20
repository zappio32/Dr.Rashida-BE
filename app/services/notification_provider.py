import uuid


class SandboxNotificationProvider:
    def send(self, *, to: str, subject: str, body: str) -> dict:
        return {"providerRef": f"sandbox-{uuid.uuid4()}"}


class TestPaymentProvider:
    def create_checkout(self, *, booking_id: str, amount: int) -> dict:
        return {"checkoutUrl": f"/payment/test?bookingId={booking_id}"}
