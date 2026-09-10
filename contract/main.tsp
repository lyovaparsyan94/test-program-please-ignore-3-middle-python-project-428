import "@typespec/http";
import "@typespec/openapi";

using TypeSpec.Http;

@service(#{ title: "Flight Booking API" })
namespace FlightBookingApi;

// ---------- Модели ----------

model City {
  code: string;
  name: string;
  country?: string;
}

model Money {
  amount: int32;
  currency: string;
}

model Airline {
  code: string;
  name: string;
}

model Flight {
  id: string;
  flightNumber: string;
  airline: Airline;
  origin: City;
  destination: City;
  departureAt: utcDateTime;
  arrivalAt: utcDateTime;
  durationMinutes: int32;
  price: Money;
  seatsAvailable: int32;
}

model Passenger {
  firstName: string;
  lastName: string;
  dateOfBirth: plainDate;
  documentNumber: string;
}

model Contact {
  email: string;
  phone: string;
}

model Booking {
  code: string;
  status: "confirmed" | "cancelled";
  flight: Flight;
  passengers: Passenger[];
  contact: Contact;
  totalPrice: Money;
  createdAt: utcDateTime;
}

// ---------- Тела запросов ----------

model BookingCreate {
  flightId: string;
  contact: Contact;

  @minItems(1)
  passengers: Passenger[];
}

model CancelRequest {
  // Необязателен по контракту: отсутствующий lastName даёт 404 (как неверный код),
  // а не отказ на входе — иначе перебором отличили бы существующий код.
  lastName?: string;
}

// ---------- Ошибки ----------

@error
model ValidationError {
  @statusCode statusCode: 400;
  code: "validation_error";
  message: string;
}

@error
model NotFoundError {
  @statusCode statusCode: 404;
  code: "not_found";
  message: string;
}

// 201 Created для успешного создания брони.
model BookingCreated {
  @statusCode statusCode: 201;
  ...Booking;
}

// ---------- Операции ----------

@route("/api/cities")
@get
op listCities(): City[];

@route("/api/flights")
@get
op searchFlights(
  @query origin: string,
  @query destination: string,
  @query date: plainDate,
  @query passengers?: int32 = 1,
): Flight[] | ValidationError;

@route("/api/flights/{id}")
@get
op getFlight(@path id: string): Flight | NotFoundError;

@route("/api/bookings")
@post
op createBooking(@body body: BookingCreate): BookingCreated | ValidationError;

@route("/api/bookings/{code}")
@get
op getBooking(@path code: string, @query lastName?: string): Booking | NotFoundError;

@route("/api/bookings/{code}/cancel")
@post
op cancelBooking(@path code: string, @body body: CancelRequest): Booking | NotFoundError;
