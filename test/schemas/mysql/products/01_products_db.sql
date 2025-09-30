START TRANSACTION;

DROP TABLE IF EXISTS `Products`;

CREATE TABLE `Products` (
  `product_id` INT PRIMARY KEY,
  `parent_product_id` INT NULL,
  `product_name` VARCHAR(80),
  `product_price` DECIMAL(19,4) DEFAULT 0.0000,
  `product_color` VARCHAR(50),
  `product_size` VARCHAR(50),
  `product_description` VARCHAR(255)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO `Products`
  (`product_id`, `parent_product_id`, `product_name`, `product_price`, `product_color`, `product_size`, `product_description`)
VALUES
  (1, 8, 'Dell monitor', 795.6200, 'Red', 'Medium', 'Latest model!'),
  (2, 3, 'Dell keyboard', 104.0000, 'Yellow', 'Medium', 'Keyboard for games!'),
  (3, 1, 'iPhone6s', 560.9300, 'Red', 'Small', 'Second hand!'),
  (4, 6, 'iWatch', 369.1100, 'Red', 'Medium', 'Designed for sports!'),
  (5, 2, 'Lenovo keyboard', 382.6700, 'Yellow', 'Medium', 'Work smartly!');

COMMIT;
