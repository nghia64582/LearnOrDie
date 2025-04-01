package MyApp.for_loop

object ForObj {
  def task1(): Unit = {
    for {
      i <- 1 to 3
      j <- 1 to 3
    } {
      println(s"$i and $j")
    }
  }

  def task2(): Unit = {
    for (i <- 1 to 3)
      println(i)
      println(2)
  }

  def main(args: Array[String]): Unit = {
    task2()
  }
}
