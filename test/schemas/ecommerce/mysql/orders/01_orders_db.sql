START TRANSACTION;

CREATE TABLE `Invoices` (
  `invoice_number` INT PRIMARY KEY,
  `invoice_status_code` VARCHAR(10) NOT NULL,
  `invoice_date` DATETIME
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `Orders` (
  `order_id` INT PRIMARY KEY,
  `customer_id` INT NOT NULL,
  `order_status_code` VARCHAR(20) NOT NULL,
  `date_order_placed` DATETIME NOT NULL,
  INDEX `idx_orders_customer_id` (`customer_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `Order_Items` (
  `order_item_id` INT PRIMARY KEY,
  `product_id` INT NOT NULL,
  `order_id` INT NOT NULL,
  `order_item_status_code` VARCHAR(20) NOT NULL,
  INDEX `idx_order_items_product_id` (`product_id`),
  INDEX `idx_order_items_order_id` (`order_id`),
  CONSTRAINT `fk_order_items_order`
    FOREIGN KEY (`order_id`) REFERENCES `Orders`(`order_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO `Invoices` (`invoice_number`, `invoice_status_code`, `invoice_date`) VALUES
  (1, 'Paid',   '2018-03-09 07:16:07'),
  (2, 'Issued', '2018-01-28 20:08:22'),
  (3, 'Paid',   '2018-02-13 02:16:55'),
  (4, 'Issued', '2018-03-11 02:04:42'),
  (5, 'Paid',   '2018-03-14 11:58:55'),
  (6, 'Paid',   '2018-02-19 22:12:45'),
  (7, 'Paid',   '2018-02-14 02:48:48'),
  (8, 'Paid',   '2018-03-20 00:29:12'),
  (9, 'Issued', '2018-02-17 13:52:46'),
  (10,'Issued', '2018-02-17 11:18:32'),
  (11,'Issued', '2018-03-04 18:54:34'),
  (12,'Paid',   '2018-03-05 20:09:18'),
  (13,'Issued', '2018-01-26 02:23:32'),
  (14,'Paid',   '2018-03-23 17:12:08'),
  (15,'Issued', '2018-02-03 05:46:16');

INSERT INTO `Orders` (`order_id`, `customer_id`, `order_status_code`, `date_order_placed`) VALUES
  (1,  5,  'Cancelled',      '2017-09-17 16:13:07'),
  (2,  13, 'Part Completed', '2017-10-14 12:05:48'),
  (3,  13, 'Cancelled',      '2017-09-10 08:27:04'),
  (4,  11, 'Delivered',      '2018-03-19 21:48:59'),
  (5,  4,  'Delivered',      '2017-09-17 07:48:34'),
  (6,  8,  'Delivered',      '2018-03-07 15:34:19'),
  (7,  4,  'Part Completed', '2017-12-02 13:40:02'),
  (8,  15, 'Part Completed', '2018-03-01 04:18:28'),
  (9,  1,  'Part Completed', '2018-03-01 05:25:55'),
  (10, 15, 'Part Completed', '2017-09-25 14:30:23'),
  (11, 2,  'Cancelled',      '2017-05-27 10:55:13'),
  (12, 10, 'Cancelled',      '2017-11-06 00:37:20'),
  (13, 6,  'Part Completed', '2017-09-26 06:53:48'),
  (14, 6,  'Delivered',      '2017-05-02 00:04:13'),
  (15, 1,  'Cancelled',      '2017-11-23 04:27:11'),
  (16, 10, 'Cancelled',      '2017-07-19 12:45:12'),
  (17, 6,  'Delivered',      '2017-10-27 11:27:07'),
  (18, 3,  'Cancelled',      '2017-05-15 15:13:44'),
  (19, 13, 'Part Completed', '2017-12-10 23:45:42'),
  (20, 10, 'Cancelled',      '2017-09-20 22:18:50');

INSERT INTO `Order_Items` (`order_item_id`, `product_id`, `order_id`, `order_item_status_code`) VALUES
  (1,  4,  8,  'Delivered'),
  (2,  3,  4,  'Out of Stock'),
  (3,  2,  7,  'Delivered'),
  (4,  1,  10, 'Out of Stock'),
  (5,  1,  3,  'Delivered'),
  (6,  1,  18, 'Delivered'),
  (7,  5,  3,  'Delivered'),
  (8,  4,  19, 'Out of Stock'),
  (9,  5,  18, 'Out of Stock'),
  (10, 3,  6,  'Delivered'),
  (11, 3,  1,  'Out of Stock'),
  (12, 5,  10, 'Out of Stock'),
  (13, 4,  17, 'Delivered'),
  (14, 1,  19, 'Out of Stock'),
  (15, 3,  20, 'Out of Stock');

COMMIT;