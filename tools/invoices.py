import stripe as _stripe

_stripe.api_version = "2016-06-15"

import logging
import time
import sys
import csv
import codecs

from itertools import groupby
from datetime import datetime, timedelta, date
from io import StringIO

from app import billing as stripe


def _format_timestamp(stripe_timestamp):
    if stripe_timestamp is None:
        return None
    date_obj = date.fromtimestamp(stripe_timestamp)
    return date_obj.strftime("%m/%d/%Y")


def _format_money(stripe_money):
    return stripe_money / 100.0


def _paginate_list(stripe_klass, num_days, **incoming_kwargs):
    now = datetime.utcnow()
    starting_from = now - timedelta(days=num_days)
    starting_timestamp = str(int(time.mktime(starting_from.timetuple())))
    created = {"gte": starting_timestamp}

    list_req_kwargs = dict(incoming_kwargs)
    has_more = True

    while has_more:
        list_response = stripe_klass.list(limit=100, created=created, **list_req_kwargs)

        for list_response_item in list_response.data:
            yield list_response_item

        has_more = list_response.has_more

        list_req_kwargs["starting_after"] = list_response_item.id


def list_charges(num_days):
    """
    List all charges that have occurred in the past specified number of days.
    """

    for charge in _paginate_list(stripe.Charge, num_days, expand=["data.invoice"]):
        yield charge


def list_refunds(num_days):
    """
    List all refunds that have occurred in the past specified number of days.
    """
    expand = ["data.charge", "data.charge.invoice"]
    for refund in _paginate_list(stripe.Refund, num_days, expand=expand):
        yield refund


def format_refund(refund):
    """
    Generator which will return one or more line items corresponding to the specified refund.
    """
    refund_period_start = None
    refund_period_end = None
    invoice_iterable = expand_invoice(refund.charge.invoice, refund.charge.amount)
    for _, period_start, period_end, _ in invoice_iterable:
        if period_start is not None and (
            period_start < refund_period_start or refund_period_start is None
        ):
            refund_period_start = period_start
        if period_end is not None and (period_end > refund_period_end or refund_period_end is None):
            refund_period_end = period_end

    card = refund.charge.source
    yield (
        refund.created,
        [
            _format_timestamp(refund.created),
            _format_timestamp(refund_period_start),
            _format_timestamp(refund_period_end),
            _format_money(-1 * refund.amount),
            "credit_card",
            "Refunded",
            None,
            refund.id,
            refund.charge.customer,
            card.address_city,
            card.address_state,
            card.address_country,
            card.address_zip,
            card.country,
        ],
    )


def _date_key(line_item):
    return line_item.start, line_item.end


def expand_invoice(invoice, total_amount):
    if invoice is None:
        yield total_amount, None, None, None
    else:
        data_iter = groupby(invoice.lines.data, lambda li: (li.period.start, li.period.end))
        for (period_start, period_end), line_items_iter in data_iter:
            line_items = list(line_items_iter)
            period_amount = sum(line_item.amount for line_item in line_items)
            yield period_amount, period_start, period_end, line_items[-1].plan


def format_charge(charge):
    """
    Generator which will return one or more line items corresponding to the line items for this
    charge.
    """
    ch_status = "Paid"
    if charge.failure_code is not None:
        ch_status = "Failed"

    card = charge.source

    # Amount remaining to be accounted for
    remaining_charge_amount = charge.amount

    discount_start = sys.maxsize
    discount_end = sys.maxsize
    discount_percent = 0
    try:
        if charge.invoice and charge.invoice.discount:
            discount_obj = charge.invoice.discount
            assert discount_obj.coupon.amount_off is None

            discount_start = discount_obj.start
            discount_end = sys.maxsize if not discount_obj.end else discount_obj.end
            discount_percent = discount_obj.coupon.percent_off / 100.0
            assert discount_percent > 0
    except AssertionError:
        logging.exception("Discount of strange variety: %s", discount_obj)
        raise

    invoice_iterable = expand_invoice(charge.invoice, charge.amount)
    for line_amount, period_start, period_end, plan in invoice_iterable:
        yield (
            charge.created,
            [
                _format_timestamp(charge.created),
                _format_timestamp(period_start),
                _format_timestamp(period_end),
                _format_money(line_amount),
                "credit_card",
                ch_status,
                plan.name if plan is not None else None,
                charge.id,
                charge.customer,
                card.address_city,
                card.address_state,
                card.address_country,
                card.address_zip,
                card.country,
            ],
        )

        remaining_charge_amount -= line_amount

        # Assumption: a discount applies if the beginning of a subscription
        # billing period is in the window when the discount is active.
        # Assumption the second: A discount is inclusive at the start second
        # and exclusive on the end second.
        #
        # I can't find docs or examples to prove or disprove either asusmption.
        if period_start >= discount_start and period_start < discount_end:
            discount_amount = -1 * line_amount * discount_percent

            try:
                assert period_start != discount_start
            except AssertionError:
                logging.exception(
                    "We found a line item which matches the discount start: %s", charge.id
                )
                raise

            try:
                assert period_start != discount_end
            except AssertionError:
                logging.exception(
                    "We found a line item which matches the discount end: %s", charge.id
                )
                raise

            discount_name = "Discount" if plan is None else "{} Discount".format(plan.name)

            yield (
                charge.created,
                [
                    _format_timestamp(charge.created),
                    _format_timestamp(period_start) if period_start is not None else None,
                    _format_timestamp(period_end) if period_end is not None else None,
                    _format_money(discount_amount),
                    "credit_card",
                    ch_status,
                    discount_name,
                    charge.id,
                    charge.customer,
                    card.address_city,
                    card.address_state,
                    card.address_country,
                    card.address_zip,
                    card.country,
                ],
            )

            remaining_charge_amount -= discount_amount

    # Make sure our line items added up to the actual charge amount
    if remaining_charge_amount != 0:
        logging.warning(
            "Unable to fully account (%s) for charge amount (%s): %s",
            remaining_charge_amount,
            charge.amount,
            charge.id,
        )


class _UnicodeWriter(object):
    """
    A CSV writer which will write rows to CSV file "f", which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    @staticmethod
    def _encode_cell(cell):
        if cell is None:
            return cell
        return str(cell).encode("utf-8")

    def writerow(self, row):
        self.writer.writerow([self._encode_cell(s) for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)


def _merge_row_streams(*row_generators):
    """
    Descending merge sort of multiple row streams in the form of (tx_date, [row data]).

    Works recursively on an arbitrary number of row streams.
    """
    if len(row_generators) == 1:
        for only_candidate in row_generators[0]:
            yield only_candidate

    else:
        my_generator = row_generators[0]
        other_generator = _merge_row_streams(*row_generators[1:])

        other_done = False

        try:
            other_next = next(other_generator)
        except StopIteration:
            other_done = True

        for my_next in my_generator:
            while not other_done and other_next[0] > my_next[0]:
                yield other_next

                try:
                    other_next = next(other_generator)
                except StopIteration:
                    other_done = True
            yield my_next

        for other_next in other_generator:
            yield other_next


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARN)

    days = 30
    if len(sys.argv) > 1:
        days = int(sys.argv[1])

    refund_rows = (
        refund_line_item
        for one_refund in list_refunds(days)
        for refund_line_item in format_refund(one_refund)
    )

    rows = (
        line_item for one_charge in list_charges(days) for line_item in format_charge(one_charge)
    )

    transaction_writer = _UnicodeWriter(sys.stdout)
    for _, row in _merge_row_streams(refund_rows, rows):
        transaction_writer.writerow(row)
        sys.stdout.flush()
