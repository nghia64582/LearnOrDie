package MyApp.future

import scala.collection.mutable.ListBuffer
import scala.concurrent.Future
import scala.util.{Failure, Random, Success}
import scala.concurrent.ExecutionContext.Implicits.global

object MyFuture {
  def main(args: Array[String]): Unit = {
//    sortByFuture()
//    foreachFuture()
    recoverWithFuture()
  }

  def recoverWithFuture(): Unit = {
    def fetchData(id: Int): Future[String] = {
      if (id == 0) Future.failed(new IllegalArgumentException("Invalid ID"))
      else Future.successful(s"Data for ID $id")
    }


    // recoverWith
    // return another future if origin future return an exception
    // do nothing if origin future return a value
    var finish: Boolean = false
    val result: Future[String] = fetchData(1).recoverWith {
      case _: IllegalArgumentException => Future.successful("Default data")
    }
    result.foreach((st) =>
      println("Value of future " + st)
      finish = true
    )
    while (!finish) {

    }

  }

  def foreachFuture(): Unit = {
    var finish: Boolean = false
    val future1: Future[String] = Future {
      Thread.sleep(1000)
      "Finish future 1"
    }
    future1.foreach(st => {
      println("Future 1 finished, value " + st)
      finish = true
    })
    var c: Int = 0
    while (!finish) {
      c += 1
      if (c % 10000000 == 0) {
        println(c)
      }
    }
  }

  def futureSample(): Unit = {

    // setup future value and async function
    val future1: Future[String] = Future {
      Thread.sleep(1000)
      "Finish future 1"
    }

    val future2: Future[String] = Future {
      Thread.sleep(1200)
      "Finish future 2"
    }

    // set up callback after future has a specific value
    future1.onComplete {
      case Success(value) => println("Success : " + value)
      case Failure(exception) => println("Exception : " + exception)
    }
    future2.onComplete {
      case Success(value) => println("Success : " + value)
      case Failure(exception) => println("Exception : " + exception)
    }

    // wait until future has some value
    while (future1.value.getOrElse(0) == 0 || future2.value.getOrElse(0) == 0) {

    }

    // print value
    println(future1.value.getOrElse(0))
    println(future2.value.getOrElse(0))
  }

  def sortByFuture(): Unit = {
    val rd: Random = new Random()
    val nums: ListBuffer[Int] = ListBuffer[Int]()
    val futures: ListBuffer[Future[Int]] = ListBuffer[Future[Int]]()
    for (i <- 1 to 10) {
      nums.addOne(rd.nextInt(5000))
    }
    for (i <- nums) {
      val future: Future[Int] = Future {
        Thread.sleep(i)
        i
      }
      future.onComplete {
        case Success(value) => println("Finish value : " + value)
        case Failure(exception) => println("Exception : " + exception)
      }
    }
    var finish: Boolean = false
    while (!finish) {
      var not_done: Boolean = false
      for (future <- futures) {
        if (future.value.getOrElse(0) == 0) {
          not_done = true
        }
      }
      if (!not_done) {
        finish = true
      }
    }
  }
}
