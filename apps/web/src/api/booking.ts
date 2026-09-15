import { apiFetch } from "./client";

export interface BookingReq {
  name: string;
  phone: string;
  storeCode?: string;
  appointmentAt?: string;
  taskId?: string;
  remark?: string;
  source?: string;
}

export const createBooking = (req: BookingReq) =>
  apiFetch<{ bookingId: number }>("/api/bookings", {
    method: "POST",
    body: JSON.stringify(req),
  });
