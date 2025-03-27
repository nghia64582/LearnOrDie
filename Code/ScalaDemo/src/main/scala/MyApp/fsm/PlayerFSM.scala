package MyApp.fsm

import akka.actor.{ActorSystem, FSM, Props}

sealed trait State
case object Idle extends State
case object Walking extends State
case object Running extends State

sealed trait Data
case object Uninitialized extends Data
case class PlayerData(speed: Int) extends Data

case object StartWalking
case object StartRunning
case object Stop


class PlayerFSM extends FSM[State, Data] {
  startWith(Idle, Uninitialized)

  when(Idle) {
    case Event(StartWalking, Uninitialized) => {
      println("StartWalking")
      goto(Walking) using PlayerData(speed = 5)
    }
  }

  when(Walking) {
    case Event(StartRunning, PlayerData(_)) => {
      println("StartRunning")
      goto(Running) using PlayerData(speed = 10)
    }
    case Event(Stop, PlayerData(_)) => {
      println("Stop")
      goto(Idle) using Uninitialized
    }
  }

  when(Running) {
    case Event(Stop, PlayerData(_)) => {
      println("Stop")
      goto(Idle) using Uninitialized
    }
  }

}

object GameFSM {
  def main(args: Array[String]): Unit = {
    val system = ActorSystem("GameSystem")
    val player = system.actorOf(Props[PlayerFSM](), "player")

    player ! StartWalking
    player ! StartRunning
    player ! Stop
  }
}
