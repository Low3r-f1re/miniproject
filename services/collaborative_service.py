import json
from typing import List, Dict, Optional, Any
from datetime import datetime
from models import TripPlan, TripParticipant, TripActivity, User
from extensions import db

class CollaborativeService:
    def __init__(self, socketio=None):
        self.socketio = socketio

    def create_trip_plan(self, creator_id: int, title: str, description: str = None,
                        start_date: str = None, end_date: str = None, budget: float = None,
                        max_participants: int = 1, is_collaborative: bool = False) -> Optional[TripPlan]:
        """Create a new trip plan"""
        try:
            trip_plan = TripPlan(
                title=title,
                description=description,
                start_date=datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else None,
                end_date=datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else None,
                budget=budget,
                max_participants=max_participants,
                is_collaborative=is_collaborative,
                creator_id=creator_id
            )

            db.session.add(trip_plan)
            db.session.commit()

            # Add creator as participant
            participant = TripParticipant(
                trip_plan_id=trip_plan.id,
                user_id=creator_id,
                role='creator'
            )
            db.session.add(participant)
            db.session.commit()

            # Notify collaborators if collaborative
            if is_collaborative:
                self._notify_trip_created(trip_plan)

            return trip_plan

        except Exception as e:
            print(f"Create trip plan error: {e}")
            db.session.rollback()
            return None

    def invite_participant(self, trip_plan_id: int, inviter_id: int, invitee_email: str) -> Dict[str, Any]:
        """Invite a user to join a trip plan"""
        try:
            # Check if trip plan exists and user has permission
            trip_plan = TripPlan.query.get(trip_plan_id)
            if not trip_plan:
                return {'success': False, 'message': 'Trip plan not found'}

            # Check if inviter is a participant
            participant = TripParticipant.query.filter_by(
                trip_plan_id=trip_plan_id,
                user_id=inviter_id
            ).first()

            if not participant:
                return {'success': False, 'message': 'You are not a participant in this trip'}

            # Find invitee
            invitee = User.query.filter_by(email=invitee_email).first()
            if not invitee:
                return {'success': False, 'message': 'User not found'}

            # Check if already invited
            existing = TripParticipant.query.filter_by(
                trip_plan_id=trip_plan_id,
                user_id=invitee.id
            ).first()

            if existing:
                return {'success': False, 'message': 'User is already a participant'}

            # Check participant limit
            current_count = TripParticipant.query.filter_by(trip_plan_id=trip_plan_id).count()
            if current_count >= trip_plan.max_participants:
                return {'success': False, 'message': 'Trip plan is full'}

            # Add participant
            new_participant = TripParticipant(
                trip_plan_id=trip_plan_id,
                user_id=invitee.id,
                role='participant'
            )

            db.session.add(new_participant)
            db.session.commit()

            # Notify participants
            self._notify_participant_joined(trip_plan_id, invitee)

            return {'success': True, 'message': f'{invitee.name} has been added to the trip'}

        except Exception as e:
            print(f"Invite participant error: {e}")
            db.session.rollback()
            return {'success': False, 'message': 'Failed to invite participant'}

    def add_trip_activity(self, trip_plan_id: int, user_id: int, activity_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add an activity to a trip plan"""
        try:
            # Check permissions
            participant = TripParticipant.query.filter_by(
                trip_plan_id=trip_plan_id,
                user_id=user_id
            ).first()

            if not participant:
                return {'success': False, 'message': 'You are not a participant in this trip'}

            # Create activity
            activity = TripActivity(
                trip_plan_id=trip_plan_id,
                destination_id=activity_data.get('destination_id'),
                title=activity_data['title'],
                description=activity_data.get('description'),
                activity_date=datetime.strptime(activity_data['date'], '%Y-%m-%d').date() if activity_data.get('date') else None,
                start_time=datetime.strptime(activity_data['start_time'], '%H:%M').time() if activity_data.get('start_time') else None,
                end_time=datetime.strptime(activity_data['end_time'], '%H:%M').time() if activity_data.get('end_time') else None,
                cost=activity_data.get('cost'),
                category=activity_data.get('category'),
                latitude=activity_data.get('latitude'),
                longitude=activity_data.get('longitude'),
                created_by=user_id
            )

            db.session.add(activity)
            db.session.commit()

            # Notify other participants
            self._notify_activity_added(trip_plan_id, activity, participant.user)

            return {'success': True, 'activity_id': activity.id, 'message': 'Activity added successfully'}

        except Exception as e:
            print(f"Add activity error: {e}")
            db.session.rollback()
            return {'success': False, 'message': 'Failed to add activity'}

    def update_trip_activity(self, activity_id: int, user_id: int, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing trip activity"""
        try:
            activity = TripActivity.query.get(activity_id)
            if not activity:
                return {'success': False, 'message': 'Activity not found'}

            # Check if user is participant in the trip
            participant = TripParticipant.query.filter_by(
                trip_plan_id=activity.trip_plan_id,
                user_id=user_id
            ).first()

            if not participant:
                return {'success': False, 'message': 'You are not authorized to update this activity'}

            # Update allowed fields
            allowed_fields = ['title', 'description', 'activity_date', 'start_time', 'end_time',
                            'cost', 'category', 'latitude', 'longitude']

            for field in allowed_fields:
                if field in updates:
                    value = updates[field]
                    if field in ['activity_date'] and value:
                        value = datetime.strptime(value, '%Y-%m-%d').date()
                    elif field in ['start_time', 'end_time'] and value:
                        value = datetime.strptime(value, '%H:%M').time()
                    elif field == 'cost' and value:
                        value = float(value)

                    setattr(activity, field, value)

            db.session.commit()

            # Notify participants
            self._notify_activity_updated(activity.trip_plan_id, activity, participant.user)

            return {'success': True, 'message': 'Activity updated successfully'}

        except Exception as e:
            print(f"Update activity error: {e}")
            db.session.rollback()
            return {'success': False, 'message': 'Failed to update activity'}

    def get_trip_plan_details(self, trip_plan_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed trip plan information for a participant"""
        try:
            # Check if user is participant
            participant = TripParticipant.query.filter_by(
                trip_plan_id=trip_plan_id,
                user_id=user_id
            ).first()

            if not participant:
                return None

            trip_plan = TripPlan.query.get(trip_plan_id)
            if not trip_plan:
                return None

            # Get all participants
            participants = TripParticipant.query.filter_by(trip_plan_id=trip_plan_id).all()
            participant_details = []
            for p in participants:
                participant_details.append({
                    'id': p.user.id,
                    'name': p.user.name,
                    'email': p.user.email,
                    'role': p.role,
                    'joined_at': p.joined_at.isoformat()
                })

            # Get all activities
            activities = TripActivity.query.filter_by(trip_plan_id=trip_plan_id).order_by(TripActivity.activity_date, TripActivity.start_time).all()
            activity_details = []
            for activity in activities:
                activity_details.append({
                    'id': activity.id,
                    'title': activity.title,
                    'description': activity.description,
                    'date': activity.activity_date.isoformat() if activity.activity_date else None,
                    'start_time': activity.start_time.strftime('%H:%M') if activity.start_time else None,
                    'end_time': activity.end_time.strftime('%H:%M') if activity.end_time else None,
                    'cost': activity.cost,
                    'category': activity.category,
                    'latitude': activity.latitude,
                    'longitude': activity.longitude,
                    'created_by': activity.created_by,
                    'created_by_name': activity.user.name if activity.user else 'Unknown'
                })

            return {
                'id': trip_plan.id,
                'title': trip_plan.title,
                'description': trip_plan.description,
                'start_date': trip_plan.start_date.isoformat() if trip_plan.start_date else None,
                'end_date': trip_plan.end_date.isoformat() if trip_plan.end_date else None,
                'budget': trip_plan.budget,
                'max_participants': trip_plan.max_participants,
                'is_collaborative': trip_plan.is_collaborative,
                'creator_id': trip_plan.creator_id,
                'creator_name': trip_plan.creator.name,
                'created_at': trip_plan.created_at.isoformat(),
                'updated_at': trip_plan.updated_at.isoformat(),
                'participants': participant_details,
                'activities': activity_details,
                'user_role': participant.role
            }

        except Exception as e:
            print(f"Get trip details error: {e}")
            return None

    def leave_trip_plan(self, trip_plan_id: int, user_id: int) -> Dict[str, Any]:
        """Remove a participant from a trip plan"""
        try:
            participant = TripParticipant.query.filter_by(
                trip_plan_id=trip_plan_id,
                user_id=user_id
            ).first()

            if not participant:
                return {'success': False, 'message': 'You are not a participant in this trip'}

            # Don't allow creator to leave
            if participant.role == 'creator':
                return {'success': False, 'message': 'Trip creator cannot leave the trip'}

            db.session.delete(participant)
            db.session.commit()

            # Notify remaining participants
            self._notify_participant_left(trip_plan_id, user_id)

            return {'success': True, 'message': 'You have left the trip'}

        except Exception as e:
            print(f"Leave trip error: {e}")
            db.session.rollback()
            return {'success': False, 'message': 'Failed to leave trip'}

    def get_user_trip_plans(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all trip plans for a user"""
        try:
            participants = TripParticipant.query.filter_by(user_id=user_id).all()
            trip_plans = []

            for participant in participants:
                trip = participant.trip_plan
                trip_plans.append({
                    'id': trip.id,
                    'title': trip.title,
                    'description': trip.description,
                    'start_date': trip.start_date.isoformat() if trip.start_date else None,
                    'end_date': trip.end_date.isoformat() if trip.end_date else None,
                    'is_collaborative': trip.is_collaborative,
                    'role': participant.role,
                    'participant_count': len(trip.participants),
                    'activity_count': len(trip.activities)
                })

            return trip_plans

        except Exception as e:
            print(f"Get user trips error: {e}")
            return []

    def _notify_trip_created(self, trip_plan: TripPlan):
        """Send notification when trip is created"""
        if self.socketio:
            self.socketio.emit('trip_created', {
                'trip_id': trip_plan.id,
                'title': trip_plan.title,
                'creator': trip_plan.creator.name
            }, room=f'trip_{trip_plan.id}')

    def _notify_participant_joined(self, trip_plan_id: int, user: User):
        """Send notification when participant joins"""
        if self.socketio:
            self.socketio.emit('participant_joined', {
                'trip_id': trip_plan_id,
                'user_id': user.id,
                'user_name': user.name
            }, room=f'trip_{trip_plan_id}')

    def _notify_participant_left(self, trip_plan_id: int, user_id: int):
        """Send notification when participant leaves"""
        if self.socketio:
            self.socketio.emit('participant_left', {
                'trip_id': trip_plan_id,
                'user_id': user_id
            }, room=f'trip_{trip_plan_id}')

    def _notify_activity_added(self, trip_plan_id: int, activity: TripActivity, user: User):
        """Send notification when activity is added"""
        if self.socketio:
            self.socketio.emit('activity_added', {
                'trip_id': trip_plan_id,
                'activity_id': activity.id,
                'title': activity.title,
                'added_by': user.name
            }, room=f'trip_{trip_plan_id}')

    def _notify_activity_updated(self, trip_plan_id: int, activity: TripActivity, user: User):
        """Send notification when activity is updated"""
        if self.socketio:
            self.socketio.emit('activity_updated', {
                'trip_id': trip_plan_id,
                'activity_id': activity.id,
                'title': activity.title,
                'updated_by': user.name
            }, room=f'trip_{trip_plan_id}')

    def send_message(self, trip_plan_id: int, user_id: int, message: str) -> Dict[str, Any]:
        """Send a message to trip participants (simplified version)"""
        try:
            participant = TripParticipant.query.filter_by(
                trip_plan_id=trip_plan_id,
                user_id=user_id
            ).first()

            if not participant:
                return {'success': False, 'message': 'You are not a participant in this trip'}

            user = User.query.get(user_id)

            # In a real app, you'd store messages in a database
            message_data = {
                'trip_id': trip_plan_id,
                'user_id': user_id,
                'user_name': user.name,
                'message': message,
                'timestamp': datetime.utcnow().isoformat()
            }

            # Send via SocketIO
            if self.socketio:
                self.socketio.emit('new_message', message_data, room=f'trip_{trip_plan_id}')

            return {'success': True, 'message': 'Message sent'}

        except Exception as e:
            print(f"Send message error: {e}")
            return {'success': False, 'message': 'Failed to send message'}
