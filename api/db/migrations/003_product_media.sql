-- migrate:up

UPDATE products SET image_url = CASE slug
    WHEN 'shampoo-tratamiento-caida' THEN '/products/shampoo-caida.svg'
    WHEN 'pomada-restauradora-barba' THEN '/products/pomada-barba.svg'
    WHEN 'shampoo-pure-detox' THEN '/products/shampoo-detox.svg'
    WHEN 'shampoo-engrosador-sin-sulfatos' THEN '/products/shampoo-grosor.svg'
    WHEN 'pomada-opaca-cabello' THEN '/products/pomada-opaca.svg'
END
WHERE slug IN ('shampoo-tratamiento-caida', 'pomada-restauradora-barba', 'shampoo-pure-detox', 'shampoo-engrosador-sin-sulfatos', 'pomada-opaca-cabello');

-- migrate:down

UPDATE products SET image_url = NULL
WHERE slug IN ('shampoo-tratamiento-caida', 'pomada-restauradora-barba', 'shampoo-pure-detox', 'shampoo-engrosador-sin-sulfatos', 'pomada-opaca-cabello');
