package MyApp.yield_exp

object TheYield {
  def main(args: Array[String]): Unit = {
    val r: List[Int] = List(1, 2, 3)

    // using yield and for-loop to return new collection from existing list
    var result: List[Int] = for (element <- r) yield element * 2
    println(result)

    // using yield with nested loop like flatMap
    var nestedLoopResult = for {
      x <- 1 to 5
      y <- 1 to 2
    } yield List(x, y)
    println(nestedLoopResult)

    // using yield with conditions to filter the value
    var filterResult = for (i <- 1 to 10 if i % 2 == 0) yield i
    println(filterResult)
  }
}
