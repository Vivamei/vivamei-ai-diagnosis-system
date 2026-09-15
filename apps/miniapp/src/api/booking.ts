import { apiRequest } from './client'

/** 与 apps/web/src/api/booking.ts 字段一一对应，后端是同一个 /api/bookings 接口。 */
export interface BookingReq {
  name: string
  phone: string
  storeCode?: string
  appointmentAt?: string
  taskId?: string
  remark?: string
  source?: string
}

export const createBooking = (req: BookingReq) =>
  apiRequest<{ bookingId: number }>('/api/bookings', { method: 'POST', data: req })
