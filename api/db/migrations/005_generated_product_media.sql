-- migrate:up

-- Packshots ficticios de demo, generados para el boilerplate y servidos desde
-- el storefront. Los nombres no contienen marcas ni assets de terceros.
UPDATE products SET image_url = CASE slug
    WHEN 'shampoo-tratamiento-caida' THEN '/products/generated/shampoo-caida.webp'
    WHEN 'pomada-restauradora-barba' THEN '/products/generated/pomada-barba.webp'
    WHEN 'shampoo-pure-detox' THEN '/products/generated/shampoo-detox.webp'
    WHEN 'shampoo-engrosador-sin-sulfatos' THEN '/products/generated/shampoo-grosor.webp'
    WHEN 'pomada-opaca-cabello' THEN '/products/generated/pomada-opaca.webp'
    ELSE image_url
END
WHERE slug IN (
    'shampoo-tratamiento-caida',
    'pomada-restauradora-barba',
    'shampoo-pure-detox',
    'shampoo-engrosador-sin-sulfatos',
    'pomada-opaca-cabello'
);

UPDATE products SET video_url = CASE slug
    WHEN 'shampoo-tratamiento-caida' THEN '/products/generated/shampoo-caida.mp4'
    WHEN 'pomada-restauradora-barba' THEN '/products/generated/pomada-barba.mp4'
    WHEN 'shampoo-pure-detox' THEN '/products/generated/shampoo-detox.mp4'
    WHEN 'shampoo-engrosador-sin-sulfatos' THEN '/products/generated/shampoo-grosor.mp4'
    WHEN 'pomada-opaca-cabello' THEN '/products/generated/pomada-opaca.mp4'
    ELSE video_url
END
WHERE slug IN (
    'shampoo-tratamiento-caida',
    'pomada-restauradora-barba',
    'shampoo-pure-detox',
    'shampoo-engrosador-sin-sulfatos',
    'pomada-opaca-cabello'
);

-- migrate:down

UPDATE products SET image_url = CASE slug
    WHEN 'shampoo-tratamiento-caida' THEN '/products/shampoo-caida.svg'
    WHEN 'pomada-restauradora-barba' THEN '/products/pomada-barba.svg'
    WHEN 'shampoo-pure-detox' THEN '/products/shampoo-detox.svg'
    WHEN 'shampoo-engrosador-sin-sulfatos' THEN '/products/shampoo-grosor.svg'
    WHEN 'pomada-opaca-cabello' THEN '/products/pomada-opaca.svg'
    ELSE image_url
END
WHERE slug IN (
    'shampoo-tratamiento-caida',
    'pomada-restauradora-barba',
    'shampoo-pure-detox',
    'shampoo-engrosador-sin-sulfatos',
    'pomada-opaca-cabello'
);

UPDATE products SET video_url = NULL
WHERE slug IN (
    'shampoo-tratamiento-caida',
    'pomada-restauradora-barba',
    'shampoo-pure-detox',
    'shampoo-engrosador-sin-sulfatos',
    'pomada-opaca-cabello'
);
