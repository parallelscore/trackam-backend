# app/api/routes/analytics.py
from sqlalchemy import and_
from datetime import datetime, timedelta, timezone
from fastapi import Depends, status, HTTPException, Query

from app.utils.logging_util import setup_logger
from app.utils.security_util import SecurityUtil
from app.api.routes.base_router import RouterManager
from app.api.models.delivery_model import DeliveryModel

from app.utils.database_operator_util import database_operator_util


security_util = SecurityUtil()
get_current_user = security_util.get_current_user


class AnalyticsRouter:

    def __init__(self):

        self.router_manager = RouterManager()
        self.logger = setup_logger(__name__)

        # Cancel a delivery
        self.router_manager.add_route(
            path="/deliveries/{tracking_id}/cancel",
            handler_method=self.cancel_delivery,
            methods=["POST"],
            tags=["analytics"],
            status_code=status.HTTP_200_OK
        )

        # Get dashboard stats
        self.router_manager.add_route(
            path="/deliveries/stats/dashboard",
            handler_method=self.get_dashboard_stats,
            methods=["GET"],
            tags=["analytics"],
            status_code=status.HTTP_200_OK
        )

        # Get delivery analytics data
        self.router_manager.add_route(
            path="/deliveries/stats/analytics",
            handler_method=self.get_delivery_analytics,
            methods=["GET"],
            tags=["analytics"],
            status_code=status.HTTP_200_OK
        )

        # Get top riders
        self.router_manager.add_route(
            path="/deliveries/stats/top-riders",
            handler_method=self.get_top_riders,
            methods=["GET"],
            tags=["analytics"],
            status_code=status.HTTP_200_OK
        )

    async def cancel_delivery(self, tracking_id: str, current_user: dict = Depends(get_current_user)):
        """
        Cancel a delivery by its tracking ID.
        """
        try:
            # Check if delivery exists and belongs to this vendor
            delivery = await database_operator_util.find_one(
                DeliveryModel,
                and_(
                    DeliveryModel.tracking_id == tracking_id,
                    DeliveryModel.vendor_id == current_user["id"]
                )
            )

            if not delivery:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Delivery not found"
                )

            # Check if delivery is already completed or cancelled
            if delivery.status in ['completed', 'cancelled']:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot cancel a delivery with status '{delivery.status}'"
                )

            # Update delivery status to cancelled
            update_data = {
                "status": "cancelled",
                "updated_at": datetime.now(timezone.utc),
                "is_tracking_active": False
            }

            await database_operator_util.update(
                model=DeliveryModel,
                filter_by={"tracking_id": tracking_id},
                data=update_data
            )

            # Get the updated delivery
            updated_delivery = await database_operator_util.find_one(
                DeliveryModel,
                DeliveryModel.tracking_id == tracking_id
            )

            return updated_delivery

        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Error cancelling delivery: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to cancel delivery"
            )

    async def get_dashboard_stats(
            self,
            period: str = Query("all", description="Time period: 'day', 'week', 'month', or 'all'"),
            current_user: dict = Depends(get_current_user)
    ):
        """
        Get dashboard statistics for vendor deliveries.
        """
        try:
            # Set time frame based on period parameter
            filter_conditions = [DeliveryModel.vendor_id == current_user["id"]]

            now = datetime.now(timezone.utc)
            if period == "day":
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
                filter_conditions.append(DeliveryModel.created_at >= start_date)
            elif period == "week":
                start_date = now - timedelta(days=7)
                filter_conditions.append(DeliveryModel.created_at >= start_date)
            elif period == "month":
                start_date = now - timedelta(days=30)
                filter_conditions.append(DeliveryModel.created_at >= start_date)

            # Get all deliveries within the time frame
            filter_expr = and_(*filter_conditions)
            deliveries = await database_operator_util.find_all(
                DeliveryModel,
                filter_expr
            )

            # Count deliveries by status
            total_deliveries = len(deliveries)
            in_progress = sum(1 for d in deliveries if d.get('status') == 'in_progress')
            completed = sum(1 for d in deliveries if d.get('status') == 'completed')
            cancelled = sum(1 for d in deliveries if d.get('status') == 'cancelled')

            # Calculate completion rate
            completion_rate = round((completed / total_deliveries * 100) if total_deliveries > 0 else 0)

            # Calculate average delivery time (for completed deliveries)
            delivery_times = []
            for d in deliveries:
                if d.get('status') == 'completed' and d.created_at and d.updated_at:
                    delivery_time = (d.updated_at - d.created_at).total_seconds() / 60  # in minutes
                    delivery_times.append(delivery_time)

            avg_delivery_time = round(sum(delivery_times) / len(delivery_times)) if delivery_times else 0

            # Calculate cancellation rate
            cancel_rate = round((cancelled / total_deliveries * 100) if total_deliveries > 0 else 0)

            return {
                "total_deliveries": total_deliveries,
                "in_progress": in_progress,
                "completed": completed,
                "cancelled": cancelled,
                "completion_rate": completion_rate,
                "avg_delivery_time": avg_delivery_time,
                "cancel_rate": cancel_rate
            }

        except Exception as e:
            self.logger.error(f"Error getting dashboard stats: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve dashboard statistics"
            )

    # Helper: shift a date (always on day=1) back by `months` full months
    async def _shift_month(self, date: datetime, months: int) -> datetime:
        year = date.year
        month = date.month - months
        # borrow years if month <= 0
        while month <= 0:
            month += 12
            year -= 1
        # return same day/hour/minute etc., but month/year adjusted
        return date.replace(year=year, month=month)

    async def get_delivery_analytics(
            self,
            time_range: str = Query("week", description="Time range: 'week', 'month', or 'year'"),
            current_user: dict = Depends(get_current_user)
    ):
        """
        Get delivery analytics data for charts.
        """
        try:
            now = datetime.now(timezone.utc)
            data = []

            if time_range == "week":
                # Get data for last 7 days
                for i in range(6, -1, -1):
                    date = now - timedelta(days=i)
                    day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
                    day_end = date.replace(hour=23, minute=59, second=59, microsecond=999999)

                    # Get deliveries for this day
                    day_deliveries = await database_operator_util.find_all(
                        DeliveryModel,
                        and_(
                            DeliveryModel.vendor_id == current_user["id"],
                            DeliveryModel.created_at >= day_start,
                            DeliveryModel.created_at <= day_end
                        )
                    )

                    # Count by status
                    created = sum(1 for d in day_deliveries if d.get('status') == 'created')
                    completed = sum(1 for d in day_deliveries if d.get('status') == 'completed')
                    in_progress = sum(1 for d in day_deliveries if d.get('status') == 'in_progress')
                    cancelled = sum(1 for d in day_deliveries if d.get('status') == 'cancelled')


                    day_name = date.strftime("%a")  # Short name of day (Mon, Tue, etc.)

                    data.append({
                        "name": day_name,
                        "created": created,
                        "completed": completed,
                        "inProgress": in_progress,
                        "cancelled": cancelled
                    })

            elif time_range == "month":
                # Get data for last 4 weeks
                for i in range(3, -1, -1):
                    week_start = now - timedelta(days=(i*7 + 6))
                    week_end = now - timedelta(days=i*7)

                    # Get deliveries for this week
                    week_deliveries = await database_operator_util.find_all(
                        DeliveryModel,
                        and_(
                            DeliveryModel.vendor_id == current_user["id"],
                            DeliveryModel.created_at >= week_start,
                            DeliveryModel.created_at <= week_end
                        )
                    )

                    # Count by status
                    created = sum(1 for d in week_deliveries if d.get('status') == 'created')
                    completed = sum(1 for d in week_deliveries if d.get('status') == 'completed')
                    in_progress = sum(1 for d in week_deliveries if d.get('status') == 'in_progress')
                    cancelled = sum(1 for d in week_deliveries if d.get('status') == 'cancelled')

                    week_name = f"Week {4-i}"

                    data.append({
                        "name": week_name,
                        "created": created,
                        "completed": completed,
                        "inProgress": in_progress,
                        "cancelled": cancelled
                    })

            elif time_range == "year":
                # compute the first instant of this month
                first_of_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

                # iterate from 11 months ago up to now
                for i in range(11, -1, -1):
                    # month_start is the first day of the month, 00:00
                    month_start = await self._shift_month(first_of_this_month, i)

                    if i == 0:
                        # current month: end at the present moment
                        month_end = now
                    else:
                        # past month: take the first of the *next* month, then step back 1 µs
                        next_month_start = await self._shift_month(first_of_this_month, i - 1)
                        month_end = next_month_start - timedelta(microseconds=1)

                    # query deliveries in [month_start, month_end]
                    month_deliveries = await database_operator_util.find_all(
                        DeliveryModel,
                        and_(
                            DeliveryModel.vendor_id == current_user["id"],
                            DeliveryModel.created_at >= month_start,
                            DeliveryModel.created_at <= month_end
                        )
                    )

                    # tally statuses
                    created     = sum(1 for d in month_deliveries if d.get('status') == 'created')
                    completed   = sum(1 for d in month_deliveries if d.get('status') == 'completed')
                    in_progress = sum(1 for d in month_deliveries if d.get('status') == 'in_progress')
                    cancelled   = sum(1 for d in month_deliveries if d.get('status') == 'cancelled')

                    # label by month (e.g. “Jan”, “Feb”)
                    month_name = month_start.strftime("%b")

                    data.append({
                        "name":       month_name,
                        "created":    created,
                        "completed":  completed,
                        "inProgress": in_progress,
                        "cancelled":  cancelled
                    })

            return data

        except Exception as e:
            self.logger.error(f"Error getting delivery analytics: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve delivery analytics"
            )

    async def get_top_riders(
            self,
            limit: int = Query(5, ge=1, le=20, description="Number of top riders to return"),
            current_user: dict = Depends(get_current_user)
    ):
        """
        Get top-performing riders based on delivery completion.
        """
        try:
            # Get all deliveries for this vendor
            deliveries = await database_operator_util.find_all(
                DeliveryModel,
                DeliveryModel.vendor_id == current_user["id"]
            )

            # Group deliveries by rider
            rider_stats = {}
            for delivery in deliveries:
                if not delivery.get("rider_id"):
                    continue

                rider_id = str(delivery.get("rider_id"))

                if rider_id not in rider_stats:
                    rider_stats[rider_id] = {
                        "id": rider_id,
                        "name": delivery.rider_name,
                        "phoneNumber": delivery.rider_phone,
                        "totalDeliveries": 0,
                        "completedDeliveries": 0,
                        "completionRate": 0,
                        "avgDeliveryTimeMinutes": 0,
                        "deliveryTimes": []
                    }

                # Update rider stats
                rider_stats[rider_id]["totalDeliveries"] += 1

                if delivery.get('status') == 'completed':
                    rider_stats[rider_id]["completedDeliveries"] += 1

                    # Calculate delivery time for completed deliveries
                    if delivery.created_at and delivery.updated_at:
                        delivery_time = (delivery.updated_at - delivery.created_at).total_seconds() / 60  # in minutes
                        rider_stats[rider_id]["deliveryTimes"].append(delivery_time)

            # Calculate completion rate and average delivery time
            for rider_id, stats in rider_stats.items():
                if stats["totalDeliveries"] > 0:
                    stats["completionRate"] = round((stats["completedDeliveries"] / stats["totalDeliveries"]) * 100)

                if stats["deliveryTimes"]:
                    stats["avgDeliveryTimeMinutes"] = round(sum(stats["deliveryTimes"]) / len(stats["deliveryTimes"]))

                # Remove the intermediate list of delivery times
                del stats["deliveryTimes"]

            # Convert to list and sort by completion rate and total deliveries
            top_riders = list(rider_stats.values())
            top_riders.sort(key=lambda x: (-x["completionRate"], -x["totalDeliveries"]))

            # Return only the top N riders with at least 2 deliveries
            filtered_riders = [r for r in top_riders if r["totalDeliveries"] >= 2]
            return filtered_riders[:limit]

        except Exception as e:
            self.logger.error(f"Error getting top riders: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve top riders"
            )