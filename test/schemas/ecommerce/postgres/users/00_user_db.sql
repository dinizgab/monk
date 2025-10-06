BEGIN;

CREATE TABLE customers (
  customer_id INTEGER PRIMARY KEY,
  gender_code VARCHAR(10) NOT NULL,
  customer_first_name VARCHAR(50),
  customer_middle_initial VARCHAR(1),
  customer_last_name VARCHAR(50),
  email_address VARCHAR(255),
  login_name VARCHAR(80),
  login_password VARCHAR(20),
  phone_number VARCHAR(255),
  address_line_1 VARCHAR(255),
  town_city VARCHAR(50),
  county VARCHAR(50),
  country VARCHAR(50)
);

INSERT INTO customers
  (customer_id, gender_code, customer_first_name, customer_middle_initial, customer_last_name,
   email_address, login_name, login_password, phone_number, address_line_1, town_city, county, country)
VALUES
  (1,  'Female',  'Carmen',   'K', 'Treutel',   'pgulgowski@example.com',          'murphy07',        '58952d0e0d28de32db3b', '(253)336-6277',           '646 Herzog Key Suite 702',         'Port Madonnahaven',    'Israel',                                        'USA'),
  (2,  'Male',    'Jace',     'P', 'Mraz',      'zwisozk@example.org',             'desmond.steuber', '7ba2e47aa0904d9fbdbf', '628-468-4228x5917',       '67899 Cassin Hollow Suite 071',    'Port Korychester',     'Palau',                                         'USA'),
  (3,  'Male',    'Vickie',   'B', 'Bergnaum',  'herzog.imogene@example.org',      'kihn.alfonso',    '83a1afbe21f5ca4cd2d5', '633-223-0975',            '395 Christophe Trail',             'Lornaland',            'Moldova',                                       'USA'),
  (4,  'Male',    'Laurianne','C', 'Pfeffer',   'columbus.hackett@example.net',    'alena46',         '877cbaac266ddb0a513f', '(874)589-9823x696',       '14173 Alize Summit',               'Jennyferchester',      'Saint Vincent and the Grenadines',              'USA'),
  (5,  'Female',  'Verner',   'V', 'Schulist',  'juliet11@example.net',            'nanderson',       'c3cf21ffb950845c7d39', '(067)124-1804',           '69426 Lewis Estates Suite 438',    'Greenfelderberg',      'South Georgia and the South Sandwich Islands',  'USA'),
  (6,  'Female',  'Zetta',    'S', 'Streich',   'melody.schuppe@example.org',      'rau.felipe',      '52a6ca3fc466757bd7da', '+50(2)2537278491',        '4672 Dwight Valleys Apt. 607',     'East Fritz',           'Afghanistan',                                   'USA'),
  (7,  'Male',    'Jailyn',   'C', 'Murray',    'nmarquardt@example.org',          'vwehner',         '372350093217369391dd', '+12(1)5491495825',        '0933 Mozelle Junctions Suite 416', 'Cliftonberg',          'Reunion',                                       'USA'),
  (8,  'Male',    'Rozella',  'S', 'Crooks',    'gilbert21@example.com',           'jcremin',         'cdda0eefb860f58bd638', '648.826.7415',             '0629 Clotilde Mission',            'Ledaville',            'Bangladesh',                                    'USA'),
  (9,  'Female',  'David',    'T', 'West',      'qkoepp@example.org',              'shanie45',        'b4380163b21bf36d5326', '1-852-557-5246x36659',    '76015 Zelma Glen Apt. 194',        'Lake Claudiefort',     'Maldives',                                      'USA'),
  (10, 'Unknown', 'America',  'N', 'Nitzsche',  'gino.cruickshank@example.org',    'zsawayn',         '9df44b9e0843940e1e87', '(352)290-2941x800',       '983 Jamil Way Apt. 732',           'Braunland',            'Swaziland',                                     'USA'),
  (11, 'Male',    'Sincere',  'B', 'Jast',      'fullrich@example.net',            'hosea87',         '6b569c0e6af548ff53f9', '342-363-4102x1883',       '56465 Raymond Cliffs',             'North Kristybury',     'Iceland',                                       'USA'),
  (12, 'Female',  'Marlen',   'W', 'Anderson',  'emmie.senger@example.net',        'hosea69',         '319dd6a930c2657792a4', '+15(7)5437690330',        '22704 Thompson Flat',              'West Polly',           'Martinique',                                    'USA'),
  (13, 'Male',    'Jamel',    'E', 'Koelpin',   'bins.nona@example.net',           'stehr.guido',     '12acbe4c1c69bbe2feb3', '134-262-9679x29311',      '275 Blick Squares',                'Lake Zechariahton',    'Niue',                                          'USA'),
  (14, 'Female',  'Angeline', 'H', 'Huel',      'veum.jalon@example.org',          'parker.providenci','d1440743ea0d14fe05cd','190.171.0323x6749',       '03217 Cummings Causeway',          'East Laura',           'Colombia',                                      'USA'),
  (15, 'Male',    'Carmine',  'A', 'Steuber',   'jwatsica@example.net',            'jewell13',        '941ccba5e40de7db4ac5', '1-004-853-7921x099',      '9318 Hyatt Flats Apt. 999',        'Oletaside',            'Dominican Republic',                            'USA');

CREATE TABLE customer_payment_methods (
  customer_id INTEGER NOT NULL,
  payment_method_code VARCHAR(50) NOT NULL,
  FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

INSERT INTO customer_payment_methods (customer_id, payment_method_code) VALUES
  (15, 'Direct Debit'),
  (1,  'Direct Debit'),
  (10, 'Direct Debit'),
  (13, 'Credit Card'),
  (9,  'Credit Card'),
  (8,  'Credit Card'),
  (13, 'Cheque'),
  (15, 'Direct Debit'),
  (4,  'Credit Card'),
  (7,  'Credit Card'),
  (6,  'Credit Card'),
  (14, 'Cheque'),
  (3,  'Credit Card'),
  (2,  'Credit Card'),
  (14, 'Direct Debit');

COMMIT;
