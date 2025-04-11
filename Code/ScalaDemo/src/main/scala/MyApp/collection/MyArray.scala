package MyApp.collection

import scala.collection.mutable.*;

object MyArray {

  def main(args: Array[String]): Unit = {
    testArray()
  }

  def testList(): Unit = {
    val arr = new ListBuffer[Int]
    for (i <- arr.indices) {
      print(s"${arr.apply(i)}, ")
    }
  }

  def testArray(): Unit = {
    val arr = new Array[Int](10)
    arr.update(2, 3)
    arr.update(1, 2)
    arr.update(0, 1)
    for (i <- arr.indices) {
      print(s"${arr.apply(i)}, ")
    }
  }

  def testVector(): Unit = {

  }

  def testArrayBuffer(): Unit = {

  }

  def testSet(): Unit = {

  }

  def testMap(): Unit = {
  }

}