package MyApp.fsm.restaurant

import akka.actor.FSM

sealed trait WaiterState
case object Idle extends WaiterState
case object MovingToGiveMenu extends WaiterState
case object WaitingForOrder extends WaiterState
case object MovingToChef extends WaiterState
case object WaitingForFood extends WaiterState
case object MovingToBringFood extends WaiterState
case object MovingToIdlePos extends WaiterState
case object WaitingForPayment extends WaiterState

sealed trait WaiterData
case object NoneData extends WaiterData
case object IdleData extends WaiterData
case class MovingData(speed: Int) extends WaiterData

// Event
sealed trait WaiterEvent
case object GuestIntoTable extends WaiterEvent

class Waiter extends FSM[WaiterState, WaiterData] {
  startWith(Idle, NoneData)

  when(Idle) {
    case Event(GuestIntoTable, IdleData) =>
      goto(MovingToGiveMenu) using MovingData(5)
  }
}
