\set ON_ERROR_STOP on

BEGIN;

DO $$
BEGIN
    IF current_database() !~ '_performance$' THEN
        RAISE EXCEPTION 'Performance seed requires a database ending in _performance';
    END IF;
    IF EXISTS (SELECT 1 FROM whatsapp_conversations LIMIT 1)
       OR EXISTS (SELECT 1 FROM customers LIMIT 1) THEN
        RAISE EXCEPTION 'Performance database is not empty; create a fresh migrated database';
    END IF;
END
$$;

INSERT INTO users (full_name, email, password_hash, role)
VALUES ('Performance Supervisor', 'performance-supervisor@faa.test', 'not-for-login', 'SUPERVISOR');

INSERT INTO products (name, is_active)
SELECT 'Performance product ' || lpad(value::text, 2, '0'), true
FROM generate_series(1, 10) AS value;

INSERT INTO customers (name, company, email, phone, province, created_at, updated_at)
SELECT
    'Performance customer ' || lpad(value::text, 6, '0'),
    'FAA benchmark ' || (value % 50),
    'performance-' || value || '@faa.test',
    '+54911' || lpad(value::text, 8, '0'),
    (ARRAY['Buenos Aires', 'Córdoba', 'Mendoza', 'Santa Fe'])[1 + value % 4],
    timestamptz '2024-01-01 12:00:00+00' + value * interval '1 minute',
    timestamptz '2024-01-01 12:00:00+00' + value * interval '1 minute'
FROM generate_series(1, :conversation_count) AS value;

WITH ranked_customers AS (
    SELECT id, row_number() OVER (ORDER BY id) AS position
    FROM customers
), ranked_products AS (
    SELECT id, row_number() OVER (ORDER BY id) AS position
    FROM products
)
INSERT INTO opportunities (
    customer_id,
    assigned_user_id,
    source,
    status,
    loss_reason,
    current_status_entered_at,
    created_at,
    updated_at
)
SELECT
    customer.id,
    (SELECT id FROM users ORDER BY id LIMIT 1),
    (CASE WHEN customer.position % 3 = 0 THEN 'WHATSAPP' ELSE 'WEB' END)::lead_source_enum,
    (ARRAY['NUEVA', 'COTIZADA', 'NEGOCIACION', 'GANADA', 'PERDIDA'])[1 + customer.position % 5]::opportunity_status_enum,
    CASE WHEN customer.position % 5 = 4 THEN 'OTRO'::loss_reason_enum ELSE NULL END,
    timestamptz '2024-01-01 12:00:00+00' + customer.position * interval '1 minute',
    timestamptz '2024-01-01 12:00:00+00' + customer.position * interval '1 minute',
    timestamptz '2024-01-01 12:00:00+00' + customer.position * interval '1 minute'
FROM ranked_customers AS customer;

WITH ranked_opportunities AS (
    SELECT id, row_number() OVER (ORDER BY id) AS position
    FROM opportunities
), ranked_products AS (
    SELECT id, row_number() OVER (ORDER BY id) AS position
    FROM products
)
INSERT INTO opportunity_products (opportunity_id, product_id, quantity_kg)
SELECT opportunity.id, product.id, 1000 + opportunity.position % 5000
FROM ranked_opportunities AS opportunity
JOIN ranked_products AS product ON product.position = 1 + opportunity.position % 10;

WITH ranked_customers AS (
    SELECT id, name, phone, row_number() OVER (ORDER BY id) AS position
    FROM customers
)
INSERT INTO whatsapp_conversations (
    customer_id,
    external_phone,
    phone_match_key,
    display_name,
    resolution_status,
    last_message_at,
    last_inbound_at,
    last_outbound_at,
    unread_count,
    waiting_for_response,
    waiting_since_at,
    window_expires_at,
    created_at,
    updated_at
)
SELECT
    id,
    phone,
    phone,
    name,
    'RESOLVED',
    timestamptz '2024-06-01 12:00:00+00' + position * interval '1 minute',
    timestamptz '2024-06-01 12:00:00+00' + position * interval '1 minute',
    timestamptz '2024-06-01 11:59:00+00' + position * interval '1 minute',
    position % 5,
    position % 2 = 0,
    CASE WHEN position % 2 = 0 THEN timestamptz '2024-06-01 12:00:00+00' + position * interval '1 minute' END,
    timestamptz '2024-06-02 12:00:00+00' + position * interval '1 minute',
    timestamptz '2024-01-01 12:00:00+00' + position * interval '1 minute',
    timestamptz '2024-06-01 12:00:00+00' + position * interval '1 minute'
FROM ranked_customers;

WITH ranked_conversations AS (
    SELECT id, customer_id FROM whatsapp_conversations
), matching_opportunities AS (
    SELECT id, customer_id FROM opportunities
)
INSERT INTO whatsapp_conversation_opportunities (
    conversation_id, opportunity_id, linked_at, linked_by_user_id, link_source
)
SELECT
    conversation.id,
    opportunity.id,
    timestamptz '2024-02-01 12:00:00+00',
    (SELECT id FROM users ORDER BY id LIMIT 1),
    'AUTO_NEW_CONTACT'
FROM ranked_conversations AS conversation
JOIN matching_opportunities AS opportunity USING (customer_id);

WITH ranked_conversations AS (
    SELECT id, row_number() OVER (ORDER BY id) AS position
    FROM whatsapp_conversations
)
INSERT INTO whatsapp_messages (
    conversation_id,
    external_message_id,
    client_generated_id,
    direction,
    message_type,
    body,
    sent_by_user_id,
    dispatch_state,
    provider_state,
    provider_message_at,
    provider_status_at,
    created_at,
    updated_at,
    origin
)
SELECT
    conversation.id,
    'wamid.performance.' || message.position,
    CASE WHEN message.position % 4 = 0
        THEN md5('performance-outbound-' || message.position)::uuid END,
    (CASE WHEN message.position % 4 = 0 THEN 'OUTBOUND' ELSE 'INBOUND' END)::whatsapp_direction_enum,
    (CASE WHEN message.position % 10 = 0 THEN 'IMAGE' ELSE 'TEXT' END)::whatsapp_message_type_enum,
    'Performance message ' || message.position,
    CASE WHEN message.position % 4 = 0
        THEN (SELECT id FROM users ORDER BY id LIMIT 1) END,
    CASE WHEN message.position % 4 = 0
        THEN 'ACCEPTED'::whatsapp_dispatch_state_enum END,
    (CASE WHEN message.position % 4 = 0 THEN 'DELIVERED' ELSE 'RECEIVED' END)::whatsapp_provider_state_enum,
    timestamptz '2024-06-01 12:00:00+00' + message.position * interval '1 second',
    timestamptz '2024-06-01 12:00:00+00' + message.position * interval '1 second',
    timestamptz '2024-06-01 12:00:00+00' + message.position * interval '1 second',
    timestamptz '2024-06-01 12:00:00+00' + message.position * interval '1 second',
    'HUMAN'
FROM generate_series(1, :message_count) AS message(position)
JOIN ranked_conversations AS conversation
    ON conversation.position = 1 + (message.position - 1) % :conversation_count;

WITH ranked_messages AS (
    SELECT id, row_number() OVER (ORDER BY id) AS position
    FROM whatsapp_messages
)
INSERT INTO whatsapp_attachments (
    message_id,
    provider_media_id,
    media_type,
    mime_type,
    filename,
    size_bytes,
    storage_key,
    storage_status,
    created_at,
    updated_at
)
SELECT
    id,
    'performance-media-' || position,
    'IMAGE',
    'image/jpeg',
    'performance-' || position || '.jpg',
    4096,
    'performance/' || position || '.jpg',
    'AVAILABLE',
    timestamptz '2024-06-01 12:00:00+00' + position * interval '1 second',
    timestamptz '2024-06-01 12:00:00+00' + position * interval '1 second'
FROM ranked_messages
WHERE position % 10 = 0;

INSERT INTO whatsapp_message_status_events (
    message_id,
    external_message_id,
    provider_state,
    occurred_at,
    received_at
)
SELECT
    id,
    external_message_id,
    'DELIVERED',
    provider_message_at,
    provider_message_at
FROM whatsapp_messages;

WITH selected_customers AS (
    SELECT id, phone, row_number() OVER (ORDER BY id) AS position
    FROM customers
    ORDER BY id
    LIMIT :broadcast_recipient_count
)
INSERT INTO whatsapp_marketing_consent_events (
    client_event_id,
    customer_id,
    normalized_phone,
    decision,
    source,
    occurred_at,
    effective_at,
    recorded_at,
    recorded_by_user_id
)
SELECT
    md5('performance-consent-' || position)::uuid,
    id,
    phone,
    'OPT_IN',
    'FAA_CRM',
    timestamptz '2024-01-01 12:00:00+00',
    timestamptz '2024-01-01 12:00:00+00',
    timestamptz '2024-01-01 12:00:00+00',
    (SELECT id FROM users ORDER BY id LIMIT 1)
FROM selected_customers;

INSERT INTO whatsapp_broadcasts (
    client_generated_id,
    label,
    template_external_id,
    template_name,
    template_language,
    template_category,
    template_provider_status,
    template_header_type,
    template_header_media_required,
    template_component_signature,
    created_by_user_id,
    created_at,
    updated_at
)
SELECT
    md5('performance-broadcast-' || value)::uuid,
    'Performance Broadcast ' || value,
    'performance-marketing',
    'performance_offer',
    'es_AR',
    'MARKETING',
    'APPROVED',
    'TEXT',
    false,
    :'template_signature',
    (SELECT id FROM users ORDER BY id LIMIT 1),
    timestamptz '2024-01-01 12:00:00+00',
    timestamptz '2024-01-01 12:00:00+00'
FROM generate_series(1, :broadcast_count) AS value;

INSERT INTO whatsapp_broadcast_template_parameters (broadcast_id, position, name, value)
SELECT id, 0, 'fecha', '31/08'
FROM whatsapp_broadcasts;

WITH selected_customers AS (
    SELECT id, name, phone
    FROM customers
    ORDER BY id
    LIMIT :broadcast_recipient_count
)
INSERT INTO whatsapp_broadcast_recipients (
    broadcast_id,
    customer_id,
    customer_display_name,
    normalized_phone,
    status,
    created_at,
    updated_at
)
SELECT
    broadcast.id,
    customer.id,
    customer.name,
    customer.phone,
    'DRAFT',
    timestamptz '2024-01-01 12:00:00+00',
    timestamptz '2024-01-01 12:00:00+00'
FROM whatsapp_broadcasts AS broadcast
CROSS JOIN selected_customers AS customer;

UPDATE whatsapp_broadcast_recipients
SET status = 'READY'
WHERE broadcast_id = (SELECT max(id) FROM whatsapp_broadcasts);

ANALYZE;

SELECT
    (SELECT count(*) FROM whatsapp_conversations) AS conversations,
    (SELECT count(*) FROM whatsapp_messages) AS messages,
    (SELECT count(*) FROM whatsapp_message_status_events) AS status_events,
    (SELECT count(*) FROM whatsapp_attachments) AS attachments,
    (SELECT count(*) FROM whatsapp_broadcast_recipients) AS broadcast_recipients;

COMMIT;
