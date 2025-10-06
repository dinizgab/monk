BEGIN;

CREATE TABLE shipments (
  shipment_id INTEGER PRIMARY KEY,
  order_id INTEGER NOT NULL,
  invoice_number INTEGER NOT NULL,
  shipment_tracking_number VARCHAR(80),
  shipment_date TIMESTAMP
);

INSERT INTO shipments (shipment_id, order_id, invoice_number, shipment_tracking_number, shipment_date) VALUES
  (1, 7, 5,  '6900', '2018-02-28 00:04:11'),
  (2, 6, 2,  '3499', '2018-03-07 01:57:14'),
  (3, 9, 4,  '5617', '2018-03-18 22:23:19'),
  (4, 8, 14, '6074', '2018-03-11 23:48:37'),
  (5, 12, 9, '3848', '2018-02-25 21:42:52'),
  (6, 15, 15,'3335', '2018-03-15 01:10:18'),
  (7, 14, 3, '8731', '2018-03-14 16:21:03'),
  (8, 12, 5, '6804', '2018-03-12 01:44:44'),
  (9, 18, 7, '4377', '2018-03-20 01:23:34'),
  (10, 4, 13, '8149', '2018-03-16 03:30:05'),
  (11, 6, 2,  '9190', '2018-02-25 19:24:52'),
  (12, 17, 13,'9206', '2018-03-20 21:01:04'),
  (13, 7, 9,  '4276', '2018-03-25 15:37:44'),
  (14, 5, 11, '9195', '2018-03-10 22:34:34'),
  (15, 6, 11, '5506', '2018-03-09 07:24:28');

CREATE TABLE shipment_items (
  shipment_id INTEGER NOT NULL,
  order_item_id INTEGER NOT NULL,
  PRIMARY KEY (shipment_id, order_item_id),
  FOREIGN KEY (shipment_id) REFERENCES shipments(shipment_id)
);

INSERT INTO shipment_items (shipment_id, order_item_id) VALUES
  (4, 4),
  (7, 14),
  (15, 9),
  (8, 14),
  (9, 15),
  (6, 14);

COMMIT;
