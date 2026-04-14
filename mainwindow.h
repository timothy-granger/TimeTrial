#ifndef MAINWINDOW_H
#define MAINWINDOW_H

#include <QMainWindow>
#include <QDateTime>
#include <QTimer>
#include <QDialog>
#include <QFileDialog>
#include <QFile>
#include <QTextStream>
#include <QKeyEvent>
#include <QDateTimeEdit>
#include <QCloseEvent>
#include <QMessageBox>
#include <QMediaPlayer>

#include "AddRiderDialog.h"
#include "DateTimeDlg.h"
#include "HintsDialogImpl.h"
#include "StarterDialog.h"

namespace Ui {
class MainWindow;
}

class MainWindow : public QMainWindow
{
    Q_OBJECT

public:
    explicit MainWindow(QWidget *parent = 0);
    ~MainWindow();

protected:

    void    keyPressEvent( QKeyEvent * );
    void    closeEvent( QCloseEvent *event );

public slots:

    void    startTimer  ( void );
    void    stopTimer   ( void );

    void    addRider    ( void );
    void    editRider   ( void );
    void    removeRider ( void );
    void    recordFinish( void );

private slots:
    void    raceTimeout( void );
    void    editStartTime( void );

    void    finishCellChanged(int,int);
    void    finishCellClicked(int,int);

    void    startListSelectionChanged(QItemSelection,QItemSelection);

    void    updateResults( void );
    void    correctScoring( void );

    void    importStartList ( void );
    void    exportStartList ( void );

    void    importFinishList( void );
    void    exportFinishList( void );

    void    exportResults   ( void );

    void    importSeriesResults( void );
    void    exportSeriesResults( void );
    void    calcSeriesResults  ( void );

private:
    Ui::MainWindow *ui;

    int     getInsertRow( int iPosition );

    AddRiderDialog  m_addRiderDlg;

    QDateTime       m_startTime;
    QDateTime       m_currentTime;

    QTimer         *m_timer;

    int             m_iCurrentRider;
    int             m_iCurrentPosition;
    double          m_dCurrentPosition;

    double          m_dCurrentCountdown;

    HintsDialogImpl m_resultsDialog;
    StarterDialog   m_starterDialog;

    QStringList     m_sSeriesPoints;
    QStringList     m_sSeriesResults;

    QMediaPlayer   *m_player;
    bool            m_bPlay;
};

#endif // MAINWINDOW_H
