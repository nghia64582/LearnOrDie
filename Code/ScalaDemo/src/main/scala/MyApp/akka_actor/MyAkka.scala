package MyApp.akka_actor

import akka.actor.{Actor, ActorRef, ActorSystem, Props}

import java.util.concurrent.ExecutorService
import scala.collection.mutable

case class MyCase(x: Int) {
  def apply(x: Int): MyCase = MyCase(x)
}

class MyActor extends Actor {
  override def receive: Receive = {
    case Double.NaN => println("NaN")
    case "hello" => println("Hello")
    case "begin" => println("Begin")
    case MyCase(5) => println("MyCase 5")
  }
}

object MyAkka {

  def main(args: Array[String]): Unit = {
    task1()
    task2()
  }

  def task1(): Unit = {
    // create actor system
    val system = ActorSystem("actorSystem")

    // create an MyActor using ActorRef
    val firstActor: ActorRef = system.actorOf(Props[FirstActor](), name = "firstActor")
    val secondActor: ActorRef = system.actorOf(Props(SecondActor(firstActor)), name = "secondActor")
    val thirdActor: ActorRef = system.actorOf(Props[ThirdActor](), name = "thirdActor")
    val myActor: ActorRef = system.actorOf(Props[MyActor](), name = "myActor")

    ActorService.register("firstActor", firstActor)
    ActorService.register("secondActor", secondActor)
    ActorService.register("thirdActor", thirdActor)

    myActor ! "hello"
    myActor ! "begin"
    myActor ! Double.NaN

//    firstActor ! 1
//    secondActor ! "a"
    // shutdown system
    system.terminate()
  }

  def task2(): Unit = {
      val secondActor: ActorRef = ActorService.getActorRef("secondActor")
      val t1: Thread = Thread(() => {
        for (i <- 1 to 100) {
          secondActor ! Pair(i, i)
        }
      })

      val t2: Thread = Thread(() => {
        for (i <- 101 to 200) {
          secondActor ! Pair(i, i)
        }
      })

      secondActor ! GetSize
      secondActor ! "a"
      secondActor ! "b"
      t1.start()
      t2.start()
      t1.join()
      t2.join()
      println("Finish 2 thread")
      Thread.sleep(2000)
      println("Send message to second actor in thread : " + Thread.currentThread().threadId())
      secondActor ! GetSize
      secondActor ! "a"
      secondActor ! "b"

      Thread.sleep(2000)
      println("Finish")
  }

  def task3(): Unit = {
    val thirdActor: ActorRef = ActorService.getActorRef("thirdActor")
    for (i <- 1 to 10) {
      println("Send message to third actor " + i)
      thirdActor ! System.nanoTime()
    }
    Thread.sleep(10000)
  }

}
