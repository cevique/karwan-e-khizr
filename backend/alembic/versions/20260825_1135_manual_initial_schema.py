"""initial_schema

Revision ID: manual001
Revises: 
Create Date: 2026-08-25 11:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import geoalchemy2

# revision identifiers, used by Alembic.
revision: str = 'manual001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('agencies',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('short_name', sa.String(length=100), nullable=True),
        sa.Column('url', sa.Text(), nullable=True),
        sa.Column('timezone', sa.String(length=50), nullable=False, server_default='Asia/Karachi'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_agencies'))
    )
    op.create_table('fare_rules',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('base_fare', sa.Float(), nullable=False),
        sa.Column('per_leg_fare', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='PKR'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_fare_rules'))
    )
    op.create_table('stops',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('location', geoalchemy2.types.Geometry(geometry_type='POINT', srid=4326, spatial_index=False, from_text='ST_GeomFromEWKT', name='geometry'), nullable=True),
        sa.Column('coordinate_source', sa.Enum('nominatim', 'curated', 'UNKNOWN', name='coordinate_source_enum'), nullable=True),
        sa.Column('coordinate_confidence', sa.Enum('HIGH', 'APPROXIMATE', 'UNKNOWN', name='coordinate_confidence_enum'), nullable=True),
        sa.Column('zone_id', sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_stops'))
    )
    op.create_table('users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('role', sa.Enum('passenger', 'admin', name='user_role_enum'), nullable=False, server_default='passenger'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_users'))
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_table('routes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('agency_id', sa.Integer(), nullable=False),
        sa.Column('short_name', sa.String(length=100), nullable=False),
        sa.Column('long_name', sa.String(length=255), nullable=True),
        sa.Column('route_type', sa.Enum('bus', 'metro', 'feeder', name='route_type_enum'), nullable=False),
        sa.Column('color', sa.String(length=7), nullable=True),
        sa.Column('text_color', sa.String(length=7), nullable=True),
        sa.Column('path', geoalchemy2.types.Geometry(geometry_type='LINESTRING', srid=4326, from_text='ST_GeomFromEWKT', name='geometry'), nullable=True),
        sa.Column('geometry_source', sa.String(length=50), nullable=True),
        sa.Column('geometry_confidence', sa.Enum('HIGH', 'APPROXIMATE', name='geometry_confidence_enum'), nullable=True),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], name=op.f('fk_routes_agency_id_agencies')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_routes'))
    )
    # op.execute('CREATE INDEX idx_routes_path ON routes USING GIST (path)')
    op.create_table('tickets',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('journey_data', sa.JSON(), nullable=False),
        sa.Column('ride_leg_count', sa.Integer(), nullable=False),
        sa.Column('fare_charged', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='PKR'),
        sa.Column('status', sa.Enum('ACTIVE', 'USED', 'EXPIRED', 'REVOKED', name='ticket_status_enum'), nullable=False, server_default='ACTIVE'),
        sa.Column('qr_payload', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_tickets_user_id_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_tickets'))
    )
    op.create_index(op.f('ix_tickets_user_id'), 'tickets', ['user_id'], unique=False)
    op.create_table('route_stops',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('route_id', sa.Integer(), nullable=False),
        sa.Column('stop_id', sa.Integer(), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('distance_along_route_m', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['route_id'], ['routes.id'], name=op.f('fk_route_stops_route_id_routes')),
        sa.ForeignKeyConstraint(['stop_id'], ['stops.id'], name=op.f('fk_route_stops_stop_id_stops')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_route_stops')),
        sa.UniqueConstraint('route_id', 'stop_id', name='uq_route_stop')
    )
    op.create_table('trips',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('route_id', sa.Integer(), nullable=False),
        sa.Column('direction_id', sa.Integer(), nullable=True),
        sa.Column('headsign', sa.String(), nullable=True),
        sa.Column('scheduled_start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.Enum('scheduled', 'active', 'completed', 'cancelled', name='trip_status_enum'), nullable=False, server_default='scheduled'),
        sa.ForeignKeyConstraint(['route_id'], ['routes.id'], name=op.f('fk_trips_route_id_routes')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_trips'))
    )
    op.create_table('stop_times',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('trip_id', sa.Integer(), nullable=False),
        sa.Column('stop_id', sa.Integer(), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('arrival_offset_s', sa.Integer(), nullable=False),
        sa.Column('departure_offset_s', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['stop_id'], ['stops.id'], name=op.f('fk_stop_times_stop_id_stops')),
        sa.ForeignKeyConstraint(['trip_id'], ['trips.id'], name=op.f('fk_stop_times_trip_id_trips')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_stop_times')),
        sa.UniqueConstraint('trip_id', 'stop_id', name='uq_trip_stop')
    )
    op.create_table('vehicles',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('label', sa.String(), nullable=False),
        sa.Column('route_id', sa.Integer(), nullable=True),
        sa.Column('trip_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.Enum('scheduled', 'active', 'completed', name='vehicle_status_enum'), nullable=False, server_default='scheduled'),
        sa.ForeignKeyConstraint(['route_id'], ['routes.id'], name=op.f('fk_vehicles_route_id_routes')),
        sa.ForeignKeyConstraint(['trip_id'], ['trips.id'], name=op.f('fk_vehicles_trip_id_trips')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_vehicles'))
    )
    op.create_table('vehicle_positions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('vehicle_id', sa.Integer(), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('bearing', sa.Float(), nullable=True),
        sa.Column('speed', sa.Float(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('source', sa.Enum('simulated', 'realtime', name='position_source_enum'), nullable=False),
        sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.id'], name=op.f('fk_vehicle_positions_vehicle_id_vehicles')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_vehicle_positions'))
    )
    op.create_index(op.f('ix_vehicle_positions_vehicle_id'), 'vehicle_positions', ['vehicle_id'], unique=False)
    op.execute('CREATE INDEX idx_stops_location ON stops USING GIST (location)')
    op.execute('CREATE INDEX idx_routes_agency_id ON routes (agency_id)')
    op.execute('CREATE INDEX idx_route_stops_route_id ON route_stops (route_id)')
    op.execute('CREATE INDEX idx_route_stops_stop_id ON route_stops (stop_id)')
    op.execute('CREATE INDEX idx_trips_route_id ON trips (route_id)')
    op.execute('CREATE INDEX idx_stop_times_trip_id ON stop_times (trip_id)')
    op.execute('CREATE INDEX idx_vehicles_route_id ON vehicles (route_id)')


def downgrade() -> None:
    op.drop_index(op.f('ix_vehicle_positions_vehicle_id'), table_name='vehicle_positions')
    op.drop_table('vehicle_positions')
    op.drop_table('vehicles')
    op.drop_table('stop_times')
    op.drop_table('trips')
    op.drop_table('route_stops')
    op.drop_index(op.f('ix_tickets_user_id'), table_name='tickets')
    op.drop_table('tickets')
    op.drop_index('idx_routes_path', table_name='routes')
    op.drop_table('routes')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    op.drop_table('stops')
    op.drop_table('fare_rules')
    op.drop_table('agencies')
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS coordinate_source_enum')
    op.execute('DROP TYPE IF EXISTS coordinate_confidence_enum')
    op.execute('DROP TYPE IF EXISTS route_type_enum')
    op.execute('DROP TYPE IF EXISTS geometry_confidence_enum')
    op.execute('DROP TYPE IF EXISTS user_role_enum')
    op.execute('DROP TYPE IF EXISTS ticket_status_enum')
    op.execute('DROP TYPE IF EXISTS trip_status_enum')
    op.execute('DROP TYPE IF EXISTS vehicle_status_enum')
    op.execute('DROP TYPE IF EXISTS position_source_enum')