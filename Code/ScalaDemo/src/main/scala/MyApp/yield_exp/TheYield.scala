package MyApp.yield_exp

object TheYield {
  def main(args: Array[String]): Unit = {
    val r: List[Int] = List(1, 2, 3)

    // using yield and for-loop to return new collection from existing list
    var result: List[Int] = for (element <- r) yield element * 2
    println(result)
  }
}
