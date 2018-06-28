# from celery import Celery
# from celery.schedules import crontab
# app=Celery()
#
#
# @app.on_after_configure.connect
# def setup_periodic_tasks(sender, **kwargs):
#     # Calls test('hello') every 10 seconds.
#     sender.add_periodic_task(10.0, test.s('hello'), name='add every 10')
#
#     # Calls test('world') every 30 seconds
#     sender.add_periodic_task(30.0, test.s('world'), expires=10)
#
#     # Executes every Monday morning at 7:30 a.m.
#     sender.add_periodic_task(
#         crontab(hour=7, minute=30, day_of_week=1),
#         test.s('Happy Mondays!'),
#     )
#
#
# @app.task
# def test(arg):
#     print(arg)


def fun(n):
    c=0
    n1,n2=0,1
    while c<n:
        a=n1
        n1,n2=n2,n1+n2
        a+=1
        print(a)



print(fun(5))
# def fun(list):
#     for i in range(len(list)-1):
#         for j in range(len(list)-i-1):
#             if list[j]>list[j+1]:
#                 list[j],list[j+1]=list[j+1],list[j]+list[j+1]
#                 return list
# list=[2,4,6,8,9]
# print(fun(list))