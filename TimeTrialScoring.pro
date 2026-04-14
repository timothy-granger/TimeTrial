#-------------------------------------------------
#
# Project created by QtCreator 2017-07-15T13:23:25
#
#-------------------------------------------------

QT       += core gui
QT       += multimedia
greaterThan(QT_MAJOR_VERSION, 4): QT += widgets

TARGET = TimeTrialScoring
TEMPLATE = app


SOURCES += main.cpp\
        mainwindow.cpp \
    AddRiderDialog.cpp \
    DateTimeDlg.cpp \
    HintsDialogImpl.cpp \
    StarterDialog.cpp

HEADERS  += mainwindow.h \
    AddRiderDialog.h \
    DateTimeDlg.h \
    HintsDialogImpl.h \
    StarterDialog.h

FORMS    += mainwindow.ui \
    AddRiderDialog.ui \
    DateTimeDlg.ui \
    HintsDialogImpl.ui \
    StarterDialog.ui

RESOURCES += \
    TimeTrialScoring.qrc
